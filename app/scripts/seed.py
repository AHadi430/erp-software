from sqlalchemy import select
from app.core.config import settings
from app.core.security import hash_password
from app.database.session import SessionLocal
from app.models.auth import User, UserRole
from app.models.finance import Account, AccountType

DEFAULT_ACCOUNTS = [
    ("1000", "Cash on Hand", AccountType.ASSET), ("1010", "Bank Account", AccountType.ASSET),
    ("1100", "Accounts Receivable", AccountType.ASSET), ("1200", "Inventory", AccountType.ASSET), ("1210", "Input Tax Receivable", AccountType.ASSET),
    ("2000", "Accounts Payable", AccountType.LIABILITY), ("2100", "Sales Tax Payable", AccountType.LIABILITY),
    ("3000", "Owner Equity", AccountType.EQUITY), ("4000", "Sales Revenue", AccountType.REVENUE), ("4010", "Sales Returns", AccountType.REVENUE), ("4100", "Inventory Adjustment Gain", AccountType.REVENUE),
    ("5000", "Cost of Goods Sold", AccountType.EXPENSE), ("5100", "Inventory Adjustment Loss", AccountType.EXPENSE), ("6000", "Operating Expenses", AccountType.EXPENSE),
]

def main():
    with SessionLocal() as db:
        if not db.scalar(select(User).where(User.email == settings.initial_admin_email.lower())):
            db.add(User(email=settings.initial_admin_email.lower(), full_name="System Administrator", password_hash=hash_password(settings.initial_admin_password), role=UserRole.ADMIN))
        for code, name, account_type in DEFAULT_ACCOUNTS:
            if not db.scalar(select(Account).where(Account.code == code)):
                db.add(Account(code=code, name=name, account_type=account_type, is_system=True))
        db.commit()
        print("Seed data is ready.")

if __name__ == "__main__":
    main()
