from __future__ import annotations

from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.invoices import PurchaseInvoice, SalesInvoice
from app.models.master import Customer, Supplier
from app.models.operations import Payment, PaymentAllocation, PaymentMethod
from app.services.invoices import ZERO, get_accounts, money, next_number, post_journal
from app.services.governance import audit, ensure_open_period


def _cash_account(accounts, method: PaymentMethod):
    return accounts["1010"] if method == PaymentMethod.BANK_TRANSFER else accounts["1000"]


def _validate_allocations(amount, allocations):
    total = money(sum((Decimal(item.amount) for item in allocations), ZERO))
    if total != money(amount):
        raise HTTPException(status_code=422, detail="Payment amount must exactly equal the total allocated to invoices")
    if not allocations:
        raise HTTPException(status_code=422, detail="At least one invoice allocation is required")


def receive_customer_payment(db: Session, payload, user_id):
    ensure_open_period(db, payload.payment_date)
    _validate_allocations(payload.amount, payload.allocations)
    with db.begin_nested():
        if not db.get(Customer, payload.customer_id):
            raise HTTPException(status_code=404, detail="Customer was not found")
        accounts = get_accounts(db, "1000", "1010", "1100")
        payment = Payment(payment_number=next_number("REC"), payment_date=payload.payment_date, amount=money(payload.amount), method=payload.method, direction="receipt", customer_id=payload.customer_id, cash_bank_account_id=_cash_account(accounts, payload.method).id, notes=payload.notes)
        db.add(payment); db.flush()
        for allocation in payload.allocations:
            invoice = db.scalar(select(SalesInvoice).where(SalesInvoice.id == allocation.invoice_id).with_for_update())
            if not invoice or invoice.customer_id != payload.customer_id or invoice.status.value != "posted":
                raise HTTPException(status_code=422, detail="Each allocation must reference a posted sales invoice for this customer")
            if invoice.due_amount <= ZERO or invoice.due_amount < allocation.amount:
                raise HTTPException(status_code=422, detail=f"Allocation exceeds the outstanding amount on {invoice.invoice_number}")
            invoice.paid_amount = money(invoice.paid_amount + allocation.amount)
            invoice.due_amount = money(invoice.due_amount - allocation.amount)
            db.add(PaymentAllocation(payment_id=payment.id, sales_invoice_id=invoice.id, amount=money(allocation.amount)))
        payment.journal_entry_id = post_journal(db, entry_date=payload.payment_date, source_type="customer_payment", source_id=str(payment.id), memo=f"Customer receipt {payment.payment_number}", user_id=user_id, lines=[(_cash_account(accounts, payload.method), payment.amount, ZERO, "Customer payment received"), (accounts["1100"], ZERO, payment.amount, "Accounts receivable settled")]).id
    audit(db, action="post", entity_type="customer_payment", entity_id=payment.id, user_id=user_id, details={"number": payment.payment_number, "amount": payment.amount}); db.commit(); db.refresh(payment)
    return payment


def pay_supplier(db: Session, payload, user_id):
    ensure_open_period(db, payload.payment_date)
    _validate_allocations(payload.amount, payload.allocations)
    with db.begin_nested():
        if not db.get(Supplier, payload.supplier_id):
            raise HTTPException(status_code=404, detail="Supplier was not found")
        accounts = get_accounts(db, "1000", "1010", "2000")
        payment = Payment(payment_number=next_number("PAY"), payment_date=payload.payment_date, amount=money(payload.amount), method=payload.method, direction="disbursement", supplier_id=payload.supplier_id, cash_bank_account_id=_cash_account(accounts, payload.method).id, notes=payload.notes)
        db.add(payment); db.flush()
        for allocation in payload.allocations:
            invoice = db.scalar(select(PurchaseInvoice).where(PurchaseInvoice.id == allocation.invoice_id).with_for_update())
            if not invoice or invoice.supplier_id != payload.supplier_id or invoice.status.value != "posted":
                raise HTTPException(status_code=422, detail="Each allocation must reference a posted purchase invoice for this supplier")
            if invoice.due_amount <= ZERO or invoice.due_amount < allocation.amount:
                raise HTTPException(status_code=422, detail=f"Allocation exceeds the outstanding amount on {invoice.invoice_number}")
            invoice.paid_amount = money(invoice.paid_amount + allocation.amount)
            invoice.due_amount = money(invoice.due_amount - allocation.amount)
            db.add(PaymentAllocation(payment_id=payment.id, purchase_invoice_id=invoice.id, amount=money(allocation.amount)))
        payment.journal_entry_id = post_journal(db, entry_date=payload.payment_date, source_type="supplier_payment", source_id=str(payment.id), memo=f"Supplier payment {payment.payment_number}", user_id=user_id, lines=[(accounts["2000"], payment.amount, ZERO, "Accounts payable settled"), (_cash_account(accounts, payload.method), ZERO, payment.amount, "Supplier payment made")]).id
    audit(db, action="post", entity_type="supplier_payment", entity_id=payment.id, user_id=user_id, details={"number": payment.payment_number, "amount": payment.amount}); db.commit(); db.refresh(payment)
    return payment
