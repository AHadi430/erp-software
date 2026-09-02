from __future__ import annotations

import uuid
from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.finance import Account
from app.models.invoices import PurchaseInvoice, PurchaseInvoiceItem, SalesInvoice, SalesInvoiceItem
from app.models.master import Product
from app.models.operations import PaymentMethod
from app.models.returns import ReturnDocument, ReturnItem, ReturnType
from app.models.token import TokenClaim, TokenClaimStatus
from app.schemas.token import TokenClaimCreate
from app.services.governance import ensure_open_period
from app.services.invoices import get_accounts, next_number, post_journal

ZERO = Decimal("0")

def _whole(value: Decimal) -> Decimal:
    value = Decimal(value or 0)
    if value != value.to_integral_value():
        raise HTTPException(status_code=409, detail="Token quantities must always be whole numbers")
    return value.to_integral_value()

def token_inventory(db: Session):
    purchase = db.scalar(select(func.coalesce(func.sum(PurchaseInvoiceItem.quantity), 0)).join(PurchaseInvoice, PurchaseInvoice.id == PurchaseInvoiceItem.purchase_invoice_id).where(PurchaseInvoice.status == "posted", PurchaseInvoiceItem.token_included.is_(True))) or ZERO
    sale = db.scalar(select(func.coalesce(func.sum(SalesInvoiceItem.quantity), 0)).join(SalesInvoice, SalesInvoice.id == SalesInvoiceItem.sales_invoice_id).where(SalesInvoice.status == "posted", SalesInvoiceItem.token_included.is_(True))) or ZERO
    sales_return = db.scalar(select(func.coalesce(func.sum(ReturnItem.quantity), 0)).join(ReturnDocument, ReturnDocument.id == ReturnItem.return_document_id).join(SalesInvoiceItem, SalesInvoiceItem.id == ReturnItem.source_line_id).where(ReturnDocument.return_type == ReturnType.SALES_RETURN, SalesInvoiceItem.token_included.is_(True))) or ZERO
    purchase_return = db.scalar(select(func.coalesce(func.sum(ReturnItem.quantity), 0)).join(ReturnDocument, ReturnDocument.id == ReturnItem.return_document_id).join(PurchaseInvoiceItem, PurchaseInvoiceItem.id == ReturnItem.source_line_id).where(ReturnDocument.return_type == ReturnType.PURCHASE_RETURN, PurchaseInvoiceItem.token_included.is_(True))) or ZERO
    claimed = db.scalar(select(func.coalesce(func.sum(TokenClaim.quantity), 0)).where(TokenClaim.status != TokenClaimStatus.VOID)) or ZERO
    purchase = _whole(purchase); sale = _whole(sale); sales_return = _whole(sales_return); purchase_return = _whole(purchase_return); claimed = _whole(claimed)
    raw_available = purchase - purchase_return - sale + sales_return - claimed
    return {"received": purchase, "issued": sale, "sales_return": sales_return, "purchase_return": purchase_return, "claimed": claimed, "available": max(ZERO, raw_available), "shortage": max(ZERO, -raw_available)}

def validate_token_line(quantity, included, value):
    if not included:
        return ZERO
    quantity = Decimal(quantity)
    if quantity != quantity.to_integral_value():
        raise HTTPException(status_code=422, detail="Token-bearing paint quantity must be a whole number")
    if Decimal(value or 0) <= ZERO:
        raise HTTPException(status_code=422, detail="Token value must be greater than zero for a token-bearing line")
    return quantity.to_integral_value()

def apply_invoice_tokens(db: Session, invoice_type: str, invoice_id: uuid.UUID, items: list[dict]):
    model = SalesInvoiceItem if invoice_type == "sale" else PurchaseInvoiceItem
    fk = model.sales_invoice_id if invoice_type == "sale" else model.purchase_invoice_id
    rows = {str(row.id): row for row in db.scalars(select(model).where(fk == invoice_id)).all()}
    for item in items:
        row = rows.get(str(item["line_id"]))
        if not row:
            raise HTTPException(status_code=404, detail="Invoice line was not found")
        include = bool(item.get("token_included", False))
        value = Decimal(str(item.get("token_value", 0))) if include else ZERO
        if include and value <= ZERO:
            product = db.get(Product, row.product_id)
            value = Decimal(product.token_value) if product else ZERO
        validate_token_line(row.quantity, include, value)
        row.token_included = include
        row.token_value = value if include else ZERO
    if invoice_type == "sale":
        available = Decimal(str(token_inventory(db)["available"]))
        current_sale = sum((Decimal(row.quantity) for row in rows.values() if row.token_included), ZERO)
        if current_sale > available + sum((Decimal(item.get("quantity", 0)) for item in []), ZERO):
            raise HTTPException(status_code=422, detail=f"Only {available} tokens are available to issue")
    db.commit()
    return token_inventory(db)

def create_claim(db: Session, payload: TokenClaimCreate, user_id):
    ensure_open_period(db, payload.claim_date)
    total = (payload.quantity * payload.token_value).quantize(Decimal("0.01"))
    with db.begin_nested():
        available = Decimal(str(token_inventory(db)["available"]))
        if payload.quantity > available:
            raise HTTPException(status_code=422, detail=f"Only {available} whole tokens are available to claim")
        claim = TokenClaim(claim_number=next_number("TOK"), claim_date=payload.claim_date, painter_name=payload.painter_name, painter_phone=payload.painter_phone, quantity=payload.quantity, token_value=payload.token_value, total_amount=total, notes=payload.notes, created_by_id=user_id)
        db.add(claim); db.flush()
    db.commit(); db.refresh(claim)
    return claim

def pay_claim(db: Session, claim_id, method: PaymentMethod, user_id):
    claim = db.get(TokenClaim, claim_id)
    if not claim or claim.status != TokenClaimStatus.PENDING:
        raise HTTPException(status_code=422, detail="Only a pending token claim can be paid")
    accounts = get_accounts(db, "1000", "1010", "6000")
    cash = accounts["1010"] if method == PaymentMethod.BANK_TRANSFER else accounts["1000"]
    entry = post_journal(db, entry_date=claim.claim_date, source_type="token_claim", source_id=str(claim.id), memo=f"Painter token reimbursement {claim.claim_number}", user_id=user_id, lines=[(accounts["6000"], claim.total_amount, ZERO, "Painter token reimbursement"), (cash, ZERO, claim.total_amount, "Token reimbursement payment")])
    claim.status = TokenClaimStatus.PAID
    claim.payment_method = method.value
    claim.journal_entry_id = entry.id
    db.commit(); db.refresh(claim)
    return claim
