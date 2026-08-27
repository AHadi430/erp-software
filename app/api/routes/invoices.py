from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.auth import User, UserRole
from app.models.invoices import PurchaseInvoice, PurchaseInvoiceItem, SalesInvoice, SalesInvoiceItem
from app.schemas.invoices import InvoiceRead, PurchaseInvoiceCreate, SalesInvoiceCreate
from app.schemas.payments import CustomerReceiptCreate, PaymentRead, SupplierPaymentCreate
from app.schemas.returns import ReturnCreate
from app.services.invoices import cancel_invoice, create_purchase, create_sale
from app.services.payments import pay_supplier, receive_customer_payment
from app.services.returns import create_purchase_return, create_sales_return

sales_router = APIRouter(prefix="/sales", tags=["sales"])
purchases_router = APIRouter(prefix="/purchases", tags=["purchases"])
sales_access = Depends(require_roles(UserRole.ADMIN, UserRole.SALESPERSON, UserRole.ACCOUNTANT))
purchase_access = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.ACCOUNTANT))

def invoice_response(invoice, item_model, fk_name: str) -> dict:
    data = {column.name: getattr(invoice, column.name) for column in invoice.__table__.columns}
    data["status"] = invoice.status.value
    data["items"] = list(invoice._sa_instance_state.session.scalars(select(item_model).where(getattr(item_model, fk_name) == invoice.id)))
    return data

@sales_router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED, dependencies=[sales_access])
def post_sale(payload: SalesInvoiceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return invoice_response(create_sale(db, payload, user.id), SalesInvoiceItem, "sales_invoice_id")

@sales_router.get("", response_model=list[InvoiceRead], dependencies=[sales_access])
def list_sales(limit: int = 50, offset: int = 0, q: Optional[str] = None, status_filter: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, db: Session = Depends(get_db)):
    query = select(SalesInvoice).order_by(SalesInvoice.invoice_date.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0))
    if q: query = query.where(SalesInvoice.invoice_number.ilike(f"%{q.strip()}%"))
    if status_filter: query = query.where(SalesInvoice.status == status_filter)
    if date_from: query = query.where(SalesInvoice.invoice_date >= date_from)
    if date_to: query = query.where(SalesInvoice.invoice_date <= date_to)
    invoices = db.scalars(query)
    return [invoice_response(invoice, SalesInvoiceItem, "sales_invoice_id") for invoice in invoices]

@sales_router.post("/{invoice_id}/cancel", response_model=InvoiceRead, dependencies=[sales_access])
def cancel_sale(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return invoice_response(cancel_invoice(db, "sale", invoice_id, user.id), SalesInvoiceItem, "sales_invoice_id")

@sales_router.post("/{invoice_id}/returns", dependencies=[sales_access])
def return_sale(invoice_id: str, payload: ReturnCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_sales_return(db, invoice_id, payload, user.id)

@sales_router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED, dependencies=[sales_access])
def receive_payment(payload: CustomerReceiptCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return receive_customer_payment(db, payload, user.id)

@purchases_router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED, dependencies=[purchase_access])
def post_purchase(payload: PurchaseInvoiceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return invoice_response(create_purchase(db, payload, user.id), PurchaseInvoiceItem, "purchase_invoice_id")

@purchases_router.get("", response_model=list[InvoiceRead], dependencies=[purchase_access])
def list_purchases(limit: int = 50, offset: int = 0, q: Optional[str] = None, status_filter: Optional[str] = None, date_from: Optional[date] = None, date_to: Optional[date] = None, db: Session = Depends(get_db)):
    query = select(PurchaseInvoice).order_by(PurchaseInvoice.invoice_date.desc()).limit(min(max(limit, 1), 200)).offset(max(offset, 0))
    if q: query = query.where(PurchaseInvoice.invoice_number.ilike(f"%{q.strip()}%"))
    if status_filter: query = query.where(PurchaseInvoice.status == status_filter)
    if date_from: query = query.where(PurchaseInvoice.invoice_date >= date_from)
    if date_to: query = query.where(PurchaseInvoice.invoice_date <= date_to)
    invoices = db.scalars(query)
    return [invoice_response(invoice, PurchaseInvoiceItem, "purchase_invoice_id") for invoice in invoices]

@purchases_router.post("/{invoice_id}/cancel", response_model=InvoiceRead, dependencies=[purchase_access])
def cancel_purchase(invoice_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return invoice_response(cancel_invoice(db, "purchase", invoice_id, user.id), PurchaseInvoiceItem, "purchase_invoice_id")

@purchases_router.post("/{invoice_id}/returns", dependencies=[purchase_access])
def return_purchase(invoice_id: str, payload: ReturnCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_purchase_return(db, invoice_id, payload, user.id)

@purchases_router.post("/payments", response_model=PaymentRead, status_code=status.HTTP_201_CREATED, dependencies=[purchase_access])
def pay_purchase(payload: SupplierPaymentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return pay_supplier(db, payload, user.id)
