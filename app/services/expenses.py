from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.expenses import CashBankTransaction, CashTransactionType, Expense, ExpenseCategory
from app.models.finance import Account
from app.services.invoices import ZERO, money, next_number, post_journal

def create_expense(db: Session, payload, user_id):
    with db.begin_nested():
        accounts = {account.id: account for account in db.scalars(select(Account).where(Account.id.in_([payload.expense_account_id, payload.cash_bank_account_id])))}
        if len(accounts) != 2: raise HTTPException(status_code=404, detail="Expense or cash/bank account was not found")
        if payload.category_id and not db.get(ExpenseCategory, payload.category_id): raise HTTPException(status_code=404, detail="Expense category was not found")
        expense = Expense(expense_number=next_number("EXP"), expense_date=payload.expense_date, description=payload.description, amount=money(payload.amount), category_id=payload.category_id, expense_account_id=payload.expense_account_id, cash_bank_account_id=payload.cash_bank_account_id, created_by_id=user_id, notes=payload.notes, journal_entry_id=None)
        db.add(expense); db.flush()
        entry = post_journal(db, entry_date=expense.expense_date, source_type="expense", source_id=str(expense.id), memo=expense.description, user_id=user_id, lines=[(accounts[payload.expense_account_id], expense.amount, ZERO, "Expense"), (accounts[payload.cash_bank_account_id], ZERO, expense.amount, "Cash/bank payment")])
        expense.journal_entry_id = entry.id
    db.commit(); db.refresh(expense); return expense

def create_cash_transaction(db: Session, payload, user_id):
    if payload.account_id == payload.offset_account_id and payload.transaction_type == CashTransactionType.TRANSFER:
        raise HTTPException(status_code=422, detail="A transfer requires two different accounts")
    with db.begin_nested():
        accounts = {account.id: account for account in db.scalars(select(Account).where(Account.id.in_([payload.account_id, payload.offset_account_id])))}
        if len(accounts) != 2: raise HTTPException(status_code=404, detail="Cash/bank or offset account was not found")
        transaction = CashBankTransaction(transaction_number=next_number("CB"), transaction_date=payload.transaction_date, transaction_type=payload.transaction_type, amount=money(payload.amount), account_id=payload.account_id, offset_account_id=payload.offset_account_id, description=payload.description, created_by_id=user_id, journal_entry_id=None)
        db.add(transaction); db.flush()
        if payload.transaction_type == CashTransactionType.RECEIPT:
            lines = [(accounts[payload.account_id], transaction.amount, ZERO, "Cash/bank receipt"), (accounts[payload.offset_account_id], ZERO, transaction.amount, "Offset account")]
        elif payload.transaction_type == CashTransactionType.PAYMENT:
            lines = [(accounts[payload.offset_account_id], transaction.amount, ZERO, "Offset account"), (accounts[payload.account_id], ZERO, transaction.amount, "Cash/bank payment")]
        else:
            lines = [(accounts[payload.account_id], ZERO, transaction.amount, "Transfer out"), (accounts[payload.offset_account_id], transaction.amount, ZERO, "Transfer in")]
        transaction.journal_entry_id = post_journal(db, entry_date=transaction.transaction_date, source_type="cash_bank_transaction", source_id=str(transaction.id), memo=transaction.description, user_id=user_id, lines=lines).id
    db.commit(); db.refresh(transaction); return transaction
