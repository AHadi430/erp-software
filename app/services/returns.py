from __future__ import annotations

from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.invoices import InvoiceStatus, PurchaseInvoice, PurchaseInvoiceItem, SalesInvoice, SalesInvoiceItem
from app.models.operations import Payment, PaymentMethod, StockMovement, StockMovementType
from app.models.returns import ReturnDocument, ReturnItem, ReturnType
from app.services.invoices import ZERO, available_stock, get_accounts, money, next_number, post_journal
from app.services.governance import audit, ensure_open_period


def _returned_quantity(db: Session, line_id) -> Decimal:
    return Decimal(db.scalar(select(func.coalesce(func.sum(ReturnItem.quantity), 0)).where(ReturnItem.source_line_id == line_id)) or 0)

def create_sales_return(db: Session, invoice_id, payload, user_id):
    ensure_open_period(db, payload.return_date)
    with db.begin_nested():
        invoice = db.scalar(select(SalesInvoice).where(SalesInvoice.id == invoice_id).with_for_update())
        if not invoice or invoice.status != InvoiceStatus.POSTED:
            raise HTTPException(status_code=422, detail="Only a posted sales invoice can be returned")
        document = ReturnDocument(return_number=next_number("SRT"), return_type=ReturnType.SALES_RETURN, return_date=payload.return_date, sales_invoice_id=invoice.id, journal_entry_id=None, notes=payload.notes, created_by_id=user_id)
        db.add(document); db.flush()
        net_total = tax_total = cost_total = ZERO
        for request_line in payload.items:
            line = db.get(SalesInvoiceItem, request_line.source_line_id)
            if not line or line.sales_invoice_id != invoice.id:
                raise HTTPException(status_code=422, detail="A return line does not belong to this sales invoice")
            if line.quantity - _returned_quantity(db, line.id) < request_line.quantity:
                raise HTTPException(status_code=422, detail="Return quantity exceeds the remaining invoice quantity")
            ratio = request_line.quantity / line.quantity
            net, tax, total, cost = money((line.line_total - line.tax_amount) * ratio), money(line.tax_amount * ratio), money(line.line_total * ratio), money(line.unit_cost * request_line.quantity)
            db.add(ReturnItem(return_document_id=document.id, source_line_id=line.id, product_id=line.product_id, description=line.description, quantity=request_line.quantity, unit_cost=line.unit_cost, net_amount=net, tax_amount=tax, line_total=total))
            db.add(StockMovement(product_id=line.product_id, movement_type=StockMovementType.SALES_RETURN, quantity=request_line.quantity, unit_cost=line.unit_cost, reference_type="sales_return", reference_id=str(document.id), occurred_on=payload.return_date, created_by_id=user_id))
            net_total += net; tax_total += tax; cost_total += cost
        document.subtotal, document.tax_total, document.grand_total = money(net_total), money(tax_total), money(net_total + tax_total)
        invoice.returned_amount = money(invoice.returned_amount + document.grand_total)
        invoice.due_amount = money(invoice.due_amount - document.grand_total)
        accounts = get_accounts(db, "1100", "1200", "2100", "4010", "5000")
        entry = post_journal(db, entry_date=payload.return_date, source_type="sales_return", source_id=str(document.id), memo=f"Sales return {document.return_number}", user_id=user_id, lines=[(accounts["4010"], document.subtotal, ZERO, "Sales return"), (accounts["2100"], document.tax_total, ZERO, "Output tax reversed"), (accounts["1100"], ZERO, document.grand_total, "Customer credit"), (accounts["1200"], cost_total, ZERO, "Inventory returned"), (accounts["5000"], ZERO, cost_total, "COGS reversed")])
        document.journal_entry_id = entry.id
    audit(db, action="post", entity_type="sales_return", entity_id=document.id, user_id=user_id, details={"number": document.return_number, "total": document.grand_total}); db.commit(); db.refresh(document)
    return document


def create_purchase_return(db: Session, invoice_id, payload, user_id):
    ensure_open_period(db, payload.return_date)
    with db.begin_nested():
        invoice = db.scalar(select(PurchaseInvoice).where(PurchaseInvoice.id == invoice_id).with_for_update())
        if not invoice or invoice.status != InvoiceStatus.POSTED:
            raise HTTPException(status_code=422, detail="Only a posted purchase invoice can be returned")
        document = ReturnDocument(return_number=next_number("PRT"), return_type=ReturnType.PURCHASE_RETURN, return_date=payload.return_date, purchase_invoice_id=invoice.id, journal_entry_id=None, notes=payload.notes, created_by_id=user_id)
        db.add(document); db.flush()
        net_total = tax_total = ZERO
        for request_line in payload.items:
            line = db.get(PurchaseInvoiceItem, request_line.source_line_id)
            if not line or line.purchase_invoice_id != invoice.id:
                raise HTTPException(status_code=422, detail="A return line does not belong to this purchase invoice")
            if line.quantity - _returned_quantity(db, line.id) < request_line.quantity:
                raise HTTPException(status_code=422, detail="Return quantity exceeds the remaining invoice quantity")
            if available_stock(db, line.product_id) < request_line.quantity:
                raise HTTPException(status_code=422, detail="Cannot return more stock than is currently available")
            ratio = request_line.quantity / line.quantity
            net, tax, total = money((line.line_total - line.tax_amount) * ratio), money(line.tax_amount * ratio), money(line.line_total * ratio)
            unit_cost = money(net / request_line.quantity)
            db.add(ReturnItem(return_document_id=document.id, source_line_id=line.id, product_id=line.product_id, description=line.description, quantity=request_line.quantity, unit_cost=unit_cost, net_amount=net, tax_amount=tax, line_total=total))
            db.add(StockMovement(product_id=line.product_id, movement_type=StockMovementType.PURCHASE_RETURN, quantity=-request_line.quantity, unit_cost=unit_cost, reference_type="purchase_return", reference_id=str(document.id), occurred_on=payload.return_date, created_by_id=user_id))
            net_total += net; tax_total += tax
        document.subtotal, document.tax_total, document.grand_total = money(net_total), money(tax_total), money(net_total + tax_total)
        invoice.returned_amount = money(invoice.returned_amount + document.grand_total)
        invoice.due_amount = money(invoice.due_amount - document.grand_total)
        accounts = get_accounts(db, "1200", "1210", "2000")
        entry = post_journal(db, entry_date=payload.return_date, source_type="purchase_return", source_id=str(document.id), memo=f"Purchase return {document.return_number}", user_id=user_id, lines=[(accounts["2000"], document.grand_total, ZERO, "Supplier credit"), (accounts["1200"], ZERO, document.subtotal, "Inventory returned to supplier"), (accounts["1210"], ZERO, document.tax_total, "Input tax reversed")])
        document.journal_entry_id = entry.id
    audit(db, action="post", entity_type="purchase_return", entity_id=document.id, user_id=user_id, details={"number": document.return_number, "total": document.grand_total}); db.commit(); db.refresh(document)
    return document


def refund_return(db: Session, return_type: ReturnType, document_id, payload, user_id):
    ensure_open_period(db, payload.refund_date)
    with db.begin_nested():
        document = db.scalar(select(ReturnDocument).where(ReturnDocument.id == document_id, ReturnDocument.return_type == return_type).with_for_update())
        if not document: raise HTTPException(status_code=404, detail="Return document was not found")
        if document.refunded_amount + payload.amount > document.grand_total: raise HTTPException(status_code=422, detail="Refund exceeds the available credit note amount")
        accounts = get_accounts(db, "1000", "1100", "2000")
        if return_type == ReturnType.SALES_RETURN:
            party = db.get(SalesInvoice, document.sales_invoice_id).customer_id
            lines = [(accounts["1100"], payload.amount, ZERO, "Customer refund"), (accounts["1000"], ZERO, payload.amount, "Cash refund")]
            direction, customer_id, supplier_id, prefix = "refund", party, None, "SRF"
        else:
            party = db.get(PurchaseInvoice, document.purchase_invoice_id).supplier_id
            lines = [(accounts["1000"], payload.amount, ZERO, "Supplier refund"), (accounts["2000"], ZERO, payload.amount, "Supplier credit settled")]
            direction, customer_id, supplier_id, prefix = "refund", None, party, "PRF"
        payment = Payment(payment_number=next_number(prefix), payment_date=payload.refund_date, amount=money(payload.amount), method=PaymentMethod.CASH, direction=direction, customer_id=customer_id, supplier_id=supplier_id, cash_bank_account_id=accounts["1000"].id, notes=payload.notes)
        db.add(payment); db.flush()
        payment.journal_entry_id = post_journal(db, entry_date=payload.refund_date, source_type="return_refund", source_id=str(document.id), memo=f"Refund against {document.return_number}", user_id=user_id, lines=lines).id
        document.refunded_amount = money(document.refunded_amount + payload.amount)
    audit(db, action="refund", entity_type="return_document", entity_id=document.id, user_id=user_id, details={"number": document.return_number, "amount": payload.amount}); db.commit(); db.refresh(document)
    return document
