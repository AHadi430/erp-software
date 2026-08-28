from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.finance import Account, JournalEntry, JournalLine, TaxRate
from app.models.invoices import InvoiceStatus, PurchaseInvoice, PurchaseInvoiceItem, SalesInvoice, SalesInvoiceItem
from app.models.master import Customer, Product, Supplier
from app.models.operations import PaymentMethod, StockMovement, StockMovementType
from app.services.governance import audit, ensure_open_period

ZERO = Decimal("0.00")
MONEY = Decimal("0.01")

def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)

def next_number(prefix: str) -> str:
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"

def get_accounts(db: Session, *codes: str) -> dict[str, Account]:
    accounts = {account.code: account for account in db.scalars(select(Account).where(Account.code.in_(codes)))}
    missing = set(codes) - accounts.keys()
    if missing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Required Chart of Accounts entries are missing: {', '.join(sorted(missing))}. Run the seed command.")
    return accounts

def post_journal(db: Session, *, entry_date, source_type: str, source_id: str, memo: str, user_id, lines: list[tuple[Account, Decimal, Decimal, str]]) -> JournalEntry:
    debits, credits = money(sum(line[1] for line in lines)), money(sum(line[2] for line in lines))
    if debits != credits or debits <= ZERO:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Journal entry is not balanced")
    entry = JournalEntry(entry_number=next_number("JE"), entry_date=entry_date, source_type=source_type, source_id=source_id, memo=memo, posted_by_id=user_id, is_posted=True)
    db.add(entry)
    db.flush()
    for account, debit, credit, description in lines:
        if debit > ZERO or credit > ZERO:
            db.add(JournalLine(journal_entry_id=entry.id, account_id=account.id, debit=money(debit), credit=money(credit), description=description))
    return entry

def available_stock(db: Session, product_id) -> Decimal:
    return Decimal(db.scalar(select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(StockMovement.product_id == product_id)) or 0)

def inventory_value(db: Session, product_id) -> Decimal:
    movements = db.scalars(select(StockMovement).where(StockMovement.product_id == product_id)).all()
    return sum((Decimal(movement.quantity) * Decimal(movement.unit_cost) for movement in movements), ZERO)

def average_inventory_cost(db: Session, product_id) -> Decimal:
    quantity = available_stock(db, product_id)
    if quantity <= ZERO:
        return ZERO
    return money(inventory_value(db, product_id) / quantity)

def resolve_product_and_rate(db: Session, item):
    product = db.scalar(select(Product).where(Product.id == item.product_id, Product.is_active.is_(True)).with_for_update())
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Active product {item.product_id} was not found")
    rate = item.tax_rate
    if rate is None and product.tax_rate_id:
        tax = db.get(TaxRate, product.tax_rate_id)
        rate = tax.rate if tax and tax.is_active else Decimal("0")
    return product, Decimal(rate or 0)

def calculate_line(quantity: Decimal, unit_price: Decimal, discount: Decimal, tax_rate: Decimal, tax_inclusive: bool):
    gross = money(quantity * unit_price)
    if discount > gross:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="A line discount cannot exceed its line amount")
    after_discount = money(gross - discount)
    tax = money(after_discount * tax_rate / (Decimal("100") + tax_rate)) if tax_inclusive and tax_rate else money(after_discount * tax_rate / Decimal("100"))
    net = money(after_discount - tax) if tax_inclusive else after_discount
    return gross, net, tax, after_discount if tax_inclusive else money(after_discount + tax)

def create_sale(db: Session, payload, user_id, invoice_number: Optional[str] = None):
    ensure_open_period(db, payload.invoice_date)
    if payload.paid_amount > ZERO and payload.payment_method is None:
        raise HTTPException(status_code=422, detail="A payment method is required for a received amount")
    # Current-user authentication may already have opened the request transaction.
    # A savepoint keeps invoice posting atomic without assuming a pristine Session.
    with db.begin_nested():
        if payload.customer_id and not db.get(Customer, payload.customer_id):
            raise HTTPException(status_code=404, detail="Customer was not found")
        invoice = SalesInvoice(invoice_number=invoice_number or next_number("SAL"), invoice_date=payload.invoice_date, customer_id=payload.customer_id, status=InvoiceStatus.POSTED, payment_method=payload.payment_method, tax_inclusive=payload.tax_inclusive, notes=payload.notes, created_by_id=user_id)
        db.add(invoice); db.flush()
        revenue = tax_total = discount_total = subtotal = cost_total = ZERO
        for item in payload.items:
            product, tax_rate = resolve_product_and_rate(db, item)
            if available_stock(db, product.id) < item.quantity:
                raise HTTPException(status_code=422, detail=f"Insufficient stock for {product.name}")
            # Sales always use the current configured selling price. The client
            # only supplies quantity/discount; this prevents price drift between
            # the inventory catalog and posted invoices.
            price = product.selling_price
            gross, net, tax, line_total = calculate_line(item.quantity, price, item.discount_amount, tax_rate, payload.tax_inclusive)
            sale_unit_cost = average_inventory_cost(db, product.id)
            cost = money(item.quantity * sale_unit_cost)
            db.add(SalesInvoiceItem(sales_invoice_id=invoice.id, product_id=product.id, description=product.name, quantity=item.quantity, unit_price=price, unit_cost=sale_unit_cost, discount_amount=item.discount_amount, tax_rate=tax_rate, tax_amount=tax, line_total=line_total))
            db.add(StockMovement(product_id=product.id, movement_type=StockMovementType.SALE, quantity=-item.quantity, unit_cost=sale_unit_cost, reference_type="sales_invoice", reference_id=str(invoice.id), occurred_on=payload.invoice_date, created_by_id=user_id))
            product.cost_price = sale_unit_cost
            subtotal += gross; discount_total += item.discount_amount; revenue += net; tax_total += tax; cost_total += cost
        invoice.subtotal, invoice.discount_total, invoice.tax_total = money(subtotal), money(discount_total), money(tax_total)
        invoice.grand_total = money(revenue + tax_total)
        if payload.paid_amount > invoice.grand_total:
            raise HTTPException(status_code=422, detail="Paid amount cannot exceed the invoice total")
        invoice.paid_amount, invoice.due_amount = money(payload.paid_amount), money(invoice.grand_total - payload.paid_amount)
        if invoice.due_amount > ZERO and not invoice.customer_id:
            raise HTTPException(status_code=422, detail="A customer is required for a credit or partially paid sale")
        accounts = get_accounts(db, "1000", "1010", "1100", "1200", "2100", "4000", "5000")
        cash = accounts["1010"] if payload.payment_method == PaymentMethod.BANK_TRANSFER else accounts["1000"]
        lines = [(cash, invoice.paid_amount, ZERO, "Sale payment"), (accounts["1100"], invoice.due_amount, ZERO, "Customer receivable"), (accounts["4000"], ZERO, revenue, "Sales revenue"), (accounts["2100"], ZERO, tax_total, "Output tax"), (accounts["5000"], cost_total, ZERO, "Cost of goods sold"), (accounts["1200"], ZERO, cost_total, "Inventory issued")]
        entry = post_journal(db, entry_date=payload.invoice_date, source_type="sales_invoice", source_id=str(invoice.id), memo=f"Sales invoice {invoice.invoice_number}", user_id=user_id, lines=lines)
        invoice.journal_entry_id = entry.id
    db.commit()
    audit(db, action="post", entity_type="sales_invoice", entity_id=invoice.id, user_id=user_id, details={"number": invoice.invoice_number, "total": invoice.grand_total}); db.commit()
    db.refresh(invoice)
    return invoice

def create_purchase(db: Session, payload, user_id, invoice_number: Optional[str] = None):
    ensure_open_period(db, payload.invoice_date)
    with db.begin_nested():
        if not db.get(Supplier, payload.supplier_id):
            raise HTTPException(status_code=404, detail="Supplier was not found")
        invoice = PurchaseInvoice(invoice_number=invoice_number or next_number("PUR"), supplier_invoice_number=payload.supplier_invoice_number, invoice_date=payload.invoice_date, supplier_id=payload.supplier_id, status=InvoiceStatus.POSTED, payment_method=payload.payment_method, tax_inclusive=payload.tax_inclusive, notes=payload.notes, created_by_id=user_id)
        db.add(invoice); db.flush()
        inventory_total = tax_total = discount_total = subtotal = ZERO
        for item in payload.items:
            product, tax_rate = resolve_product_and_rate(db, item)
            if item.unit_price is None:
                raise HTTPException(status_code=422, detail="Purchase line unit price is required")
            gross, net, tax, line_total = calculate_line(item.quantity, item.unit_price, item.discount_amount, tax_rate, payload.tax_inclusive)
            unit_cost = money(net / item.quantity)
            existing_quantity = available_stock(db, product.id)
            existing_value = inventory_value(db, product.id)
            db.add(PurchaseInvoiceItem(purchase_invoice_id=invoice.id, product_id=product.id, description=product.name, quantity=item.quantity, unit_price=item.unit_price, discount_amount=item.discount_amount, tax_rate=tax_rate, tax_amount=tax, line_total=line_total))
            db.add(StockMovement(product_id=product.id, movement_type=StockMovementType.PURCHASE, quantity=item.quantity, unit_cost=unit_cost, reference_type="purchase_invoice", reference_id=str(invoice.id), occurred_on=payload.invoice_date, created_by_id=user_id))
            product.cost_price = money((existing_value + (item.quantity * unit_cost)) / (existing_quantity + item.quantity)) if existing_quantity + item.quantity > ZERO else unit_cost
            subtotal += gross; discount_total += item.discount_amount; inventory_total += net; tax_total += tax
        invoice.subtotal, invoice.discount_total, invoice.tax_total = money(subtotal), money(discount_total), money(tax_total)
        invoice.grand_total = money(inventory_total + tax_total)
        if payload.paid_amount > invoice.grand_total:
            raise HTTPException(status_code=422, detail="Paid amount cannot exceed the invoice total")
        invoice.paid_amount, invoice.due_amount = money(payload.paid_amount), money(invoice.grand_total - payload.paid_amount)
        accounts = get_accounts(db, "1000", "1010", "1200", "1210", "2000")
        cash = accounts["1010"] if payload.payment_method == PaymentMethod.BANK_TRANSFER else accounts["1000"]
        lines = [(accounts["1200"], inventory_total, ZERO, "Inventory received"), (accounts["1210"], tax_total, ZERO, "Input tax"), (cash, ZERO, invoice.paid_amount, "Purchase payment"), (accounts["2000"], ZERO, invoice.due_amount, "Supplier payable")]
        entry = post_journal(db, entry_date=payload.invoice_date, source_type="purchase_invoice", source_id=str(invoice.id), memo=f"Purchase invoice {invoice.invoice_number}", user_id=user_id, lines=lines)
        invoice.journal_entry_id = entry.id
    db.commit()
    audit(db, action="post", entity_type="purchase_invoice", entity_id=invoice.id, user_id=user_id, details={"number": invoice.invoice_number, "total": invoice.grand_total}); db.commit()
    db.refresh(invoice)
    return invoice


def save_draft(db: Session, invoice_type: str, payload, user_id, invoice_id=None):
    """Save an editable draft without affecting stock, balances, or journals."""
    invoice_model, item_model, prefix, party_field, item_fk = (SalesInvoice, SalesInvoiceItem, "SAL", "customer_id", "sales_invoice_id") if invoice_type == "sale" else (PurchaseInvoice, PurchaseInvoiceItem, "PUR", "supplier_id", "purchase_invoice_id")
    with db.begin_nested():
        if invoice_id:
            invoice = db.scalar(select(invoice_model).where(invoice_model.id == invoice_id).with_for_update())
            if not invoice or invoice.status != InvoiceStatus.DRAFT: raise HTTPException(status_code=422, detail="Only a draft invoice can be edited")
            db.query(item_model).filter(getattr(item_model, item_fk) == invoice.id).delete(synchronize_session=False)
        else:
            invoice = invoice_model(invoice_number=next_number(prefix), status=InvoiceStatus.DRAFT, created_by_id=user_id)
            db.add(invoice); db.flush()
        if invoice_type == "sale" and payload.customer_id and not db.get(Customer, payload.customer_id): raise HTTPException(status_code=404, detail="Customer was not found")
        if invoice_type == "purchase" and not db.get(Supplier, payload.supplier_id): raise HTTPException(status_code=404, detail="Supplier was not found")
        invoice.invoice_date, invoice.payment_method, invoice.tax_inclusive, invoice.notes = payload.invoice_date, payload.payment_method, payload.tax_inclusive, payload.notes
        setattr(invoice, party_field, getattr(payload, party_field))
        if invoice_type == "purchase": invoice.supplier_invoice_number = payload.supplier_invoice_number
        subtotal = discount = tax_total = net_total = ZERO
        for item in payload.items:
            product, tax_rate = resolve_product_and_rate(db, item)
            price = product.selling_price if invoice_type == "sale" else item.unit_price
            if price is None: raise HTTPException(status_code=422, detail="Purchase line unit price is required")
            gross, net, tax, line_total = calculate_line(item.quantity, price, item.discount_amount, tax_rate, payload.tax_inclusive)
            values = dict(product_id=product.id, description=product.name, quantity=item.quantity, unit_price=price, discount_amount=item.discount_amount, tax_rate=tax_rate, tax_amount=tax, line_total=line_total)
            if invoice_type == "sale": values.update(sales_invoice_id=invoice.id, unit_cost=ZERO)
            else: values.update(purchase_invoice_id=invoice.id)
            db.add(item_model(**values)); subtotal += gross; discount += item.discount_amount; tax_total += tax; net_total += net
        invoice.subtotal, invoice.discount_total, invoice.tax_total, invoice.grand_total = money(subtotal), money(discount), money(tax_total), money(net_total + tax_total)
        invoice.paid_amount, invoice.due_amount = ZERO, invoice.grand_total
    audit(db, action="save_draft", entity_type=f"{invoice_type}_invoice", entity_id=invoice.id, user_id=user_id, details={"number": invoice.invoice_number}); db.commit(); db.refresh(invoice)
    return invoice


def post_draft(db: Session, invoice_type: str, invoice_id, user_id):
    invoice_model, item_model, party_field, item_fk = (SalesInvoice, SalesInvoiceItem, "customer_id", "sales_invoice_id") if invoice_type == "sale" else (PurchaseInvoice, PurchaseInvoiceItem, "supplier_id", "purchase_invoice_id")
    invoice = db.get(invoice_model, invoice_id)
    if not invoice or invoice.status != InvoiceStatus.DRAFT: raise HTTPException(status_code=422, detail="Only a draft invoice can be posted")
    items = list(db.scalars(select(item_model).where(getattr(item_model, item_fk) == invoice.id)))
    payload = SimpleNamespace(**{party_field: getattr(invoice, party_field), "invoice_date": invoice.invoice_date, "payment_method": invoice.payment_method, "paid_amount": ZERO, "tax_inclusive": invoice.tax_inclusive, "notes": invoice.notes, "items": [SimpleNamespace(product_id=x.product_id, quantity=x.quantity, unit_price=x.unit_price, discount_amount=x.discount_amount, tax_rate=x.tax_rate) for x in items], **({"supplier_invoice_number": invoice.supplier_invoice_number} if invoice_type == "purchase" else {})})
    number = invoice.invoice_number
    db.delete(invoice); db.flush()
    return create_sale(db, payload, user_id, number) if invoice_type == "sale" else create_purchase(db, payload, user_id, number)


def cancel_invoice(db: Session, invoice_type: str, invoice_id, user_id):
    invoice_model, item_model, movement_type, source_type = (
        (SalesInvoice, SalesInvoiceItem, StockMovementType.SALES_RETURN, "sales_invoice_cancellation")
        if invoice_type == "sale" else (PurchaseInvoice, PurchaseInvoiceItem, StockMovementType.PURCHASE_RETURN, "purchase_invoice_cancellation")
    )
    with db.begin_nested():
        invoice = db.scalar(select(invoice_model).where(invoice_model.id == invoice_id).with_for_update())
        if not invoice or invoice.status != InvoiceStatus.POSTED:
            raise HTTPException(status_code=422, detail="Only a posted invoice can be cancelled")
        ensure_open_period(db, invoice.invoice_date)
        if invoice.paid_amount > ZERO or invoice.returned_amount > ZERO:
            raise HTTPException(status_code=422, detail="Cancel an invoice only before payments or returns; use return/payment workflows instead")
        original_lines = list(db.scalars(select(JournalLine).where(JournalLine.journal_entry_id == invoice.journal_entry_id)))
        if not original_lines:
            raise HTTPException(status_code=409, detail="Invoice has no journal entry to reverse")
        accounts = {account.id: account for account in db.scalars(select(Account).where(Account.id.in_([line.account_id for line in original_lines])))}
        reversal_lines = [(accounts[line.account_id], line.credit, line.debit, f"Cancellation of {invoice.invoice_number}") for line in original_lines]
        entry = post_journal(db, entry_date=invoice.invoice_date, source_type=source_type, source_id=str(invoice.id), memo=f"Cancellation of {invoice.invoice_number}", user_id=user_id, lines=reversal_lines)
        invoice.status = InvoiceStatus.CANCELLED
        invoice.due_amount = ZERO
        fk_name = "sales_invoice_id" if invoice_type == "sale" else "purchase_invoice_id"
        for item in db.scalars(select(item_model).where(getattr(item_model, fk_name) == invoice.id)):
            if invoice_type == "purchase" and available_stock(db, item.product_id) < item.quantity:
                raise HTTPException(status_code=422, detail="Cannot cancel this purchase because some received stock has already been issued")
            quantity = item.quantity if invoice_type == "sale" else -item.quantity
            unit_cost = item.unit_cost if invoice_type == "sale" else money((item.line_total - item.tax_amount) / item.quantity)
            db.add(StockMovement(product_id=item.product_id, movement_type=movement_type, quantity=quantity, unit_cost=unit_cost, reference_type=source_type, reference_id=str(invoice.id), occurred_on=invoice.invoice_date, created_by_id=user_id))
    audit(db, action="cancel", entity_type=f"{invoice_type}_invoice", entity_id=invoice.id, user_id=user_id, details={"number": invoice.invoice_number}); db.commit(); db.refresh(invoice)
    return invoice
