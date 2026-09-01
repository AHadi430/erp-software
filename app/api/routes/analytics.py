from __future__ import annotations

from collections import defaultdict
from datetime import date
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database.session import get_db
from app.models.invoices import PurchaseInvoice, PurchaseInvoiceItem, SalesInvoice, SalesInvoiceItem, InvoiceStatus
from app.models.master import Customer, Supplier
from app.models.operations import Payment
from app.models.returns import ReturnDocument, ReturnItem, ReturnType

router = APIRouter(prefix="/reports", tags=["performance"], dependencies=[Depends(get_current_user)])
ZERO = Decimal("0.00")


def _money(value: Decimal) -> Decimal:
    return Decimal(value or 0).quantize(Decimal("0.01"))


def _month_keys() -> list[str]:
    today = date.today()
    return [f"{today.year if today.month - offset > 0 else today.year - 1}-{((today.month - offset - 1) % 12) + 1:02d}" for offset in range(11, -1, -1)]


def customer_performance(db: Session, customer_id=None):
    customers = list(db.scalars(select(Customer).where(Customer.is_active.is_(True)).order_by(Customer.name)))
    if customer_id:
        customers = [customer for customer in customers if str(customer.id) == str(customer_id)]
    result = {str(customer.id): {"id": str(customer.id), "name": customer.name, "phone": customer.phone, "invoice_count": 0, "quantity": ZERO, "gross_sales": ZERO, "returns": ZERO, "net_sales": ZERO, "cogs": ZERO, "gross_profit": ZERO, "margin_pct": ZERO, "current_due": ZERO, "payments_received": ZERO, "monthly": defaultdict(lambda: ZERO), "yearly": defaultdict(lambda: ZERO)} for customer in customers}
    if not result:
        return []

    invoices = db.scalars(select(SalesInvoice).where(SalesInvoice.status == InvoiceStatus.POSTED)).all()
    for invoice in invoices:
        key = str(invoice.customer_id) if invoice.customer_id else None
        if key not in result:
            continue
        row = result[key]
        row["invoice_count"] += 1
        row["current_due"] += Decimal(invoice.due_amount or 0)
        items = db.scalars(select(SalesInvoiceItem).where(SalesInvoiceItem.sales_invoice_id == invoice.id)).all()
        for item in items:
            net = Decimal(item.line_total or 0) - Decimal(item.tax_amount or 0)
            cogs = Decimal(item.quantity or 0) * Decimal(item.unit_cost or 0)
            row["quantity"] += Decimal(item.quantity or 0)
            row["gross_sales"] += Decimal(item.line_total or 0)
            row["net_sales"] += net
            row["cogs"] += cogs
            row["gross_profit"] += net - cogs
            key_month = invoice.invoice_date.strftime("%Y-%m")
            row["monthly"][key_month] += net
            row["yearly"][str(invoice.invoice_date.year)] += net

    returns = db.scalars(select(ReturnDocument).where(ReturnDocument.return_type == ReturnType.SALES_RETURN)).all()
    for document in returns:
        invoice = db.get(SalesInvoice, document.sales_invoice_id)
        key = str(invoice.customer_id) if invoice and invoice.customer_id else None
        if key not in result:
            continue
        row = result[key]
        items = db.scalars(select(ReturnItem).where(ReturnItem.return_document_id == document.id)).all()
        for item in items:
            net = Decimal(item.net_amount or 0)
            cogs = Decimal(item.quantity or 0) * Decimal(item.unit_cost or 0)
            row["returns"] += Decimal(item.line_total or 0)
            row["net_sales"] -= net
            row["cogs"] -= cogs
            row["gross_profit"] -= net - cogs
            row["quantity"] -= Decimal(item.quantity or 0)
            key_month = document.return_date.strftime("%Y-%m")
            row["monthly"][key_month] -= net
            row["yearly"][str(document.return_date.year)] -= net

    payments = db.scalars(select(Payment).where(Payment.direction == "receipt", Payment.customer_id.is_not(None))).all()
    for payment in payments:
        key = str(payment.customer_id)
        if key in result:
            result[key]["payments_received"] += Decimal(payment.amount or 0)

    months = _month_keys()
    output = []
    for row in result.values():
        row["gross_profit"] = _money(row["gross_profit"])
        row["margin_pct"] = _money((row["gross_profit"] / row["net_sales"] * 100) if row["net_sales"] else ZERO)
        row["current_due"] = _money(row["current_due"])
        for field in ("gross_sales", "returns", "net_sales", "cogs", "payments_received"):
            row[field] = _money(row[field])
        row["quantity"] = _money(row["quantity"])
        row["monthly"] = [{"month": month, "volume": _money(row["monthly"][month])} for month in months]
        row["yearly"] = [{"year": year, "volume": _money(value)} for year, value in sorted(row["yearly"].items())]
        output.append(row)
    return output


def supplier_performance(db: Session, supplier_id=None):
    suppliers = list(db.scalars(select(Supplier).where(Supplier.is_active.is_(True)).order_by(Supplier.name)))
    if supplier_id:
        suppliers = [supplier for supplier in suppliers if str(supplier.id) == str(supplier_id)]
    result = {str(supplier.id): {"id": str(supplier.id), "name": supplier.name, "phone": supplier.phone, "invoice_count": 0, "quantity": ZERO, "gross_purchases": ZERO, "returns": ZERO, "net_purchases": ZERO, "current_due": ZERO, "payments_made": ZERO, "monthly": defaultdict(lambda: ZERO), "yearly": defaultdict(lambda: ZERO)} for supplier in suppliers}
    if not result:
        return []

    invoices = db.scalars(select(PurchaseInvoice).where(PurchaseInvoice.status == InvoiceStatus.POSTED)).all()
    for invoice in invoices:
        key = str(invoice.supplier_id)
        if key not in result:
            continue
        row = result[key]
        row["invoice_count"] += 1
        row["current_due"] += Decimal(invoice.due_amount or 0)
        items = db.scalars(select(PurchaseInvoiceItem).where(PurchaseInvoiceItem.purchase_invoice_id == invoice.id)).all()
        for item in items:
            net = Decimal(item.line_total or 0) - Decimal(item.tax_amount or 0)
            row["quantity"] += Decimal(item.quantity or 0)
            row["gross_purchases"] += Decimal(item.line_total or 0)
            row["net_purchases"] += net
            month = invoice.invoice_date.strftime("%Y-%m")
            row["monthly"][month] += net
            row["yearly"][str(invoice.invoice_date.year)] += net

    returns = db.scalars(select(ReturnDocument).where(ReturnDocument.return_type == ReturnType.PURCHASE_RETURN)).all()
    for document in returns:
        invoice = db.get(PurchaseInvoice, document.purchase_invoice_id)
        key = str(invoice.supplier_id) if invoice else None
        if key not in result:
            continue
        row = result[key]
        items = db.scalars(select(ReturnItem).where(ReturnItem.return_document_id == document.id)).all()
        for item in items:
            net = Decimal(item.net_amount or 0)
            row["returns"] += Decimal(item.line_total or 0)
            row["net_purchases"] -= net
            row["quantity"] -= Decimal(item.quantity or 0)
            month = document.return_date.strftime("%Y-%m")
            row["monthly"][month] -= net
            row["yearly"][str(document.return_date.year)] -= net

    payments = db.scalars(select(Payment).where(Payment.direction == "disbursement", Payment.supplier_id.is_not(None))).all()
    for payment in payments:
        key = str(payment.supplier_id)
        if key in result:
            result[key]["payments_made"] += Decimal(payment.amount or 0)

    months = _month_keys()
    output = []
    for row in result.values():
        for field in ("gross_purchases", "returns", "net_purchases", "current_due", "payments_made"):
            row[field] = _money(row[field])
        row["quantity"] = _money(row["quantity"])
        row["monthly"] = [{"month": month, "volume": _money(row["monthly"][month])} for month in months]
        row["yearly"] = [{"year": year, "volume": _money(value)} for year, value in sorted(row["yearly"].items())]
        output.append(row)
    return output


@router.get("/customer-performance")
def customer_performance_report(customer_id: str | None = None, db: Session = Depends(get_db)):
    return customer_performance(db, customer_id)


@router.get("/supplier-performance")
def supplier_performance_report(supplier_id: str | None = None, db: Session = Depends(get_db)):
    return supplier_performance(db, supplier_id)
