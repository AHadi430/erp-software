from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.auth import User, UserRole
from app.models.finance import Account, AccountType, JournalLine, TaxRate
from app.models.expenses import CashBankTransaction, Expense, ExpenseCategory
from app.models.invoices import PurchaseInvoice, PurchaseInvoiceItem, SalesInvoice, SalesInvoiceItem
from app.models.master import Customer, Supplier
from app.models.operations import Payment, PaymentAllocation, StockMovement
from app.models.returns import ReturnDocument, ReturnType
from app.models.settings import BusinessSettings
from app.schemas.inventory import StockAdjustmentCreate, StockItemRead
from app.schemas.settings import BusinessSettingsRead, BusinessSettingsUpdate, TaxRateCreate, TaxRateRead
from app.schemas.expenses import CashTransactionCreate, ExpenseCategoryCreate, ExpenseCreate
from app.services.inventory import adjust_stock, inventory_snapshot
from app.services.pdf import render_invoice_pdf
from app.services.expenses import create_cash_transaction, create_expense

inventory_router = APIRouter(prefix="/inventory", tags=["inventory"], dependencies=[Depends(get_current_user)])
reports_router = APIRouter(prefix="/reports", tags=["reports"], dependencies=[Depends(get_current_user)])
settings_router = APIRouter(prefix="/settings", tags=["settings"], dependencies=[Depends(get_current_user)])
admin_access = Depends(require_roles(UserRole.ADMIN))
inventory_access = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.ACCOUNTANT))
accounting_access = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT))

@inventory_router.get("/stock", response_model=list[StockItemRead], dependencies=[inventory_access])
def stock(db: Session = Depends(get_db)):
    return inventory_snapshot(db)

@inventory_router.post("/adjustments", status_code=status.HTTP_201_CREATED, dependencies=[inventory_access])
def adjustment(payload: StockAdjustmentCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return adjust_stock(db, payload, user.id)

@inventory_router.get("/movements", dependencies=[inventory_access])
def movements(limit: int = 100, db: Session = Depends(get_db)):
    return list(db.scalars(select(StockMovement).order_by(StockMovement.occurred_on.desc(), StockMovement.created_at.desc()).limit(min(max(limit, 1), 500))))

@reports_router.get("/expenses")
def expenses_report(db: Session = Depends(get_db)):
    return list(db.scalars(select(Expense).order_by(Expense.expense_date.desc(), Expense.created_at.desc())))

@reports_router.get("/accounts")
def accounts_report(db: Session = Depends(get_db)):
    return [{"id": account.id, "code": account.code, "name": account.name, "type": account.account_type.value, "active": account.is_active} for account in db.scalars(select(Account).where(Account.is_active.is_(True)).order_by(Account.code))]

@reports_router.get("/cash-bank-transactions")
def cash_bank_transactions(db: Session = Depends(get_db)):
    return list(db.scalars(select(CashBankTransaction).order_by(CashBankTransaction.transaction_date.desc(), CashBankTransaction.created_at.desc())))

@settings_router.get("/expense-categories", dependencies=[accounting_access])
def expense_categories(db: Session = Depends(get_db)):
    return list(db.scalars(select(ExpenseCategory).where(ExpenseCategory.is_active.is_(True)).order_by(ExpenseCategory.name)))

@settings_router.post("/expense-categories", status_code=status.HTTP_201_CREATED, dependencies=[accounting_access])
def create_expense_category(payload: ExpenseCategoryCreate, db: Session = Depends(get_db)):
    if db.scalar(select(ExpenseCategory).where(ExpenseCategory.name == payload.name)):
        raise HTTPException(status_code=409, detail="Expense category already exists")
    category = ExpenseCategory(name=payload.name); db.add(category); db.commit(); db.refresh(category); return category

@reports_router.post("/expenses", status_code=status.HTTP_201_CREATED, dependencies=[accounting_access])
def post_expense(payload: ExpenseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_expense(db, payload, user.id)

@reports_router.post("/cash-bank-transactions", status_code=status.HTTP_201_CREATED, dependencies=[accounting_access])
def post_cash_bank_transaction(payload: CashTransactionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_cash_transaction(db, payload, user.id)

def _balances(db: Session):
    rows = db.execute(select(Account, func.coalesce(func.sum(JournalLine.debit), 0), func.coalesce(func.sum(JournalLine.credit), 0)).outerjoin(JournalLine, JournalLine.account_id == Account.id).group_by(Account.id).order_by(Account.code)).all()
    result = []
    for account, debit, credit in rows:
        natural = debit - credit if account.account_type in {AccountType.ASSET, AccountType.EXPENSE} else credit - debit
        result.append({"code": account.code, "name": account.name, "type": account.account_type.value, "debit": debit, "credit": credit, "balance": natural})
    return result

@reports_router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    month_start = date.today().replace(day=1)
    sales_today = db.scalar(select(func.coalesce(func.sum(SalesInvoice.grand_total), 0)).where(SalesInvoice.invoice_date == date.today(), SalesInvoice.status == "posted"))
    sales_month = db.scalar(select(func.coalesce(func.sum(SalesInvoice.grand_total), 0)).where(SalesInvoice.invoice_date >= month_start, SalesInvoice.status == "posted"))
    purchases_month = db.scalar(select(func.coalesce(func.sum(PurchaseInvoice.grand_total), 0)).where(PurchaseInvoice.invoice_date >= month_start, PurchaseInvoice.status == "posted"))
    balances = {line["code"]: line["balance"] for line in _balances(db)}
    stock_rows = inventory_snapshot(db)
    revenue, cogs, expenses = balances.get("4000", 0) + balances.get("4010", 0), balances.get("5000", 0), balances.get("6000", 0) + balances.get("5100", 0)
    return {"sales_today": sales_today, "sales_month": sales_month, "purchases_month": purchases_month, "inventory_value": sum(row["value"] for row in stock_rows), "cash_balance": balances.get("1000", 0), "bank_balance": balances.get("1010", 0), "receivables": sum(invoice.due_amount for invoice in db.scalars(select(SalesInvoice).where(SalesInvoice.status == "posted"))), "payables": sum(invoice.due_amount for invoice in db.scalars(select(PurchaseInvoice).where(PurchaseInvoice.status == "posted"))), "gross_profit": revenue - cogs, "net_profit": revenue - cogs - expenses, "low_stock": [row for row in stock_rows if row["is_low_stock"]]}

@reports_router.get("/trial-balance")
def trial_balance(db: Session = Depends(get_db)):
    return _balances(db)

@reports_router.get("/profit-loss")
def profit_loss(db: Session = Depends(get_db)):
    rows = _balances(db); revenue = [row for row in rows if row["type"] == "revenue"]; expenses = [row for row in rows if row["type"] == "expense"]
    return {"revenue": revenue, "expenses": expenses, "total_revenue": sum(row["balance"] for row in revenue), "total_expenses": sum(row["balance"] for row in expenses), "net_profit": sum(row["balance"] for row in revenue) - sum(row["balance"] for row in expenses)}

@reports_router.get("/balance-sheet")
def balance_sheet(db: Session = Depends(get_db)):
    rows = _balances(db)
    grouped = {kind: [row for row in rows if row["type"] == kind] for kind in ("asset", "liability", "equity")}
    return {**grouped, "total_assets": sum(row["balance"] for row in grouped["asset"]), "total_liabilities": sum(row["balance"] for row in grouped["liability"]), "total_equity": sum(row["balance"] for row in grouped["equity"])}

@reports_router.get("/receivables")
def receivables(db: Session = Depends(get_db)):
    return [{"invoice_number": invoice.invoice_number, "invoice_date": invoice.invoice_date, "customer_id": invoice.customer_id, "due_amount": invoice.due_amount} for invoice in db.scalars(select(SalesInvoice).where(SalesInvoice.due_amount != 0, SalesInvoice.status == "posted"))]

@reports_router.get("/payables")
def payables(db: Session = Depends(get_db)):
    return [{"invoice_number": invoice.invoice_number, "invoice_date": invoice.invoice_date, "supplier_id": invoice.supplier_id, "due_amount": invoice.due_amount} for invoice in db.scalars(select(PurchaseInvoice).where(PurchaseInvoice.due_amount != 0, PurchaseInvoice.status == "posted"))]

@reports_router.get("/customers/{customer_id}/ledger")
def customer_ledger(customer_id: str, db: Session = Depends(get_db)):
    if not db.get(Customer, customer_id): raise HTTPException(status_code=404, detail="Customer was not found")
    invoices = [{"date": invoice.invoice_date, "reference": invoice.invoice_number, "type": "sale", "debit": invoice.grand_total, "credit": 0, "balance": invoice.due_amount} for invoice in db.scalars(select(SalesInvoice).where(SalesInvoice.customer_id == customer_id))]
    receipts = [{"date": payment.payment_date, "reference": payment.payment_number, "type": "receipt", "debit": 0, "credit": allocation.amount} for allocation, payment in db.execute(select(PaymentAllocation, Payment).join(Payment, Payment.id == PaymentAllocation.payment_id).where(Payment.customer_id == customer_id, Payment.direction == "receipt"))]
    returns = [{"date": document.return_date, "reference": document.return_number, "type": "sales_return", "debit": 0, "credit": document.grand_total} for document in db.scalars(select(ReturnDocument).join(SalesInvoice, SalesInvoice.id == ReturnDocument.sales_invoice_id).where(SalesInvoice.customer_id == customer_id, ReturnDocument.return_type == ReturnType.SALES_RETURN))]
    return {"customer_id": customer_id, "entries": sorted(invoices + receipts + returns, key=lambda item: (item["date"], item["reference"])), "outstanding": sum(item["balance"] for item in invoices)}

@reports_router.get("/suppliers/{supplier_id}/ledger")
def supplier_ledger(supplier_id: str, db: Session = Depends(get_db)):
    if not db.get(Supplier, supplier_id): raise HTTPException(status_code=404, detail="Supplier was not found")
    invoices = [{"date": invoice.invoice_date, "reference": invoice.invoice_number, "type": "purchase", "debit": 0, "credit": invoice.grand_total, "balance": invoice.due_amount} for invoice in db.scalars(select(PurchaseInvoice).where(PurchaseInvoice.supplier_id == supplier_id))]
    payments = [{"date": payment.payment_date, "reference": payment.payment_number, "type": "payment", "debit": allocation.amount, "credit": 0} for allocation, payment in db.execute(select(PaymentAllocation, Payment).join(Payment, Payment.id == PaymentAllocation.payment_id).where(Payment.supplier_id == supplier_id, Payment.direction == "disbursement"))]
    returns = [{"date": document.return_date, "reference": document.return_number, "type": "purchase_return", "debit": document.grand_total, "credit": 0} for document in db.scalars(select(ReturnDocument).join(PurchaseInvoice, PurchaseInvoice.id == ReturnDocument.purchase_invoice_id).where(PurchaseInvoice.supplier_id == supplier_id, ReturnDocument.return_type == ReturnType.PURCHASE_RETURN))]
    return {"supplier_id": supplier_id, "entries": sorted(invoices + payments + returns, key=lambda item: (item["date"], item["reference"])), "outstanding": sum(item["balance"] for item in invoices)}

def _business(db: Session):
    business = db.scalar(select(BusinessSettings))
    if not business:
        business = BusinessSettings(); db.add(business); db.commit(); db.refresh(business)
    return business

@settings_router.get("/business", response_model=BusinessSettingsRead, dependencies=[admin_access])
def business_settings(db: Session = Depends(get_db)):
    return _business(db)

@settings_router.put("/business", response_model=BusinessSettingsRead, dependencies=[admin_access])
def update_business(payload: BusinessSettingsUpdate, db: Session = Depends(get_db)):
    business = _business(db)
    for field, value in payload.model_dump().items(): setattr(business, field, value)
    db.commit(); db.refresh(business); return business

@settings_router.get("/tax-rates", response_model=list[TaxRateRead], dependencies=[admin_access])
def tax_rates(db: Session = Depends(get_db)):
    return list(db.scalars(select(TaxRate).order_by(TaxRate.name)))

@settings_router.post("/tax-rates", response_model=TaxRateRead, status_code=status.HTTP_201_CREATED, dependencies=[admin_access])
def create_tax_rate(payload: TaxRateCreate, db: Session = Depends(get_db)):
    if db.scalar(select(TaxRate).where(TaxRate.name == payload.name)):
        raise HTTPException(status_code=409, detail="Tax rate name already exists")
    record = TaxRate(**payload.model_dump()); db.add(record); db.commit(); db.refresh(record); return record

def _pdf_response(db: Session, invoice_model, item_model, invoice_id, party_model, party_field, title):
    invoice = db.get(invoice_model, invoice_id)
    if not invoice: raise HTTPException(status_code=404, detail="Invoice was not found")
    party = db.get(party_model, getattr(invoice, party_field)) if getattr(invoice, party_field) else None
    items = list(db.scalars(select(item_model).where(getattr(item_model, "sales_invoice_id" if invoice_model is SalesInvoice else "purchase_invoice_id") == invoice.id)))
    return Response(render_invoice_pdf(business=_business(db), invoice=invoice, items=items, party_name=party.name if party else "Walk-in customer", title=title), media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{invoice.invoice_number}.pdf"'})

@reports_router.get("/sales/{invoice_id}/pdf")
def sales_pdf(invoice_id: str, db: Session = Depends(get_db)):
    return _pdf_response(db, SalesInvoice, SalesInvoiceItem, invoice_id, Customer, "customer_id", "SALES INVOICE")

@reports_router.get("/purchases/{invoice_id}/pdf")
def purchase_pdf(invoice_id: str, db: Session = Depends(get_db)):
    return _pdf_response(db, PurchaseInvoice, PurchaseInvoiceItem, invoice_id, Supplier, "supplier_id", "PURCHASE INVOICE")
