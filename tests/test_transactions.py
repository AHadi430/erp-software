import unittest
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database.base import Base
import app.models
from app.models.auth import User, UserRole
from app.models.finance import Account, AccountType, JournalLine
from app.models.master import Customer, Product, Supplier
from app.models.operations import StockMovement
from app.schemas.invoices import PurchaseInvoiceCreate, SalesInvoiceCreate
from app.services.invoices import create_purchase, create_sale
from app.services.inventory import inventory_snapshot


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(email="admin@example.com", full_name="Admin", password_hash="x", role=UserRole.ADMIN)
        self.product = Product(sku="P-1", name="Interior Emulsion", selling_price=Decimal("200"), cost_price=Decimal("0"))
        self.supplier = Supplier(name="Supplier")
        self.customer = Customer(name="Customer")
        self.db.add_all([self.user, self.product, self.supplier, self.customer])
        accounts = [("1000", AccountType.ASSET), ("1010", AccountType.ASSET), ("1100", AccountType.ASSET), ("1200", AccountType.ASSET), ("1210", AccountType.ASSET), ("2000", AccountType.LIABILITY), ("2100", AccountType.LIABILITY), ("4000", AccountType.REVENUE), ("4010", AccountType.REVENUE), ("4100", AccountType.REVENUE), ("5000", AccountType.EXPENSE), ("5100", AccountType.EXPENSE)]
        self.db.add_all(Account(code=code, name=code, account_type=kind) for code, kind in accounts)
        self.db.commit()
        for entity in (self.user, self.product, self.supplier, self.customer): self.db.refresh(entity)

    def tearDown(self):
        self.db.close(); self.engine.dispose()

    def test_weighted_cost_and_balanced_journals(self):
        create_purchase(self.db, PurchaseInvoiceCreate(supplier_id=self.supplier.id, items=[{"product_id": self.product.id, "quantity": 10, "unit_price": 100}]), self.user.id)
        create_purchase(self.db, PurchaseInvoiceCreate(supplier_id=self.supplier.id, items=[{"product_id": self.product.id, "quantity": 10, "unit_price": 200}]), self.user.id)
        self.assertEqual(inventory_snapshot(self.db)[0]["unit_cost"], Decimal("150.00"))
        sale = create_sale(self.db, SalesInvoiceCreate(customer_id=self.customer.id, items=[{"product_id": self.product.id, "quantity": 2, "unit_price": 200}]), self.user.id)
        self.assertEqual(self.db.scalar(select(func.sum(StockMovement.quantity))), Decimal("18.000"))
        debit, credit = self.db.execute(select(func.sum(JournalLine.debit), func.sum(JournalLine.credit)).where(JournalLine.journal_entry_id == sale.journal_entry_id)).one()
        self.assertEqual(debit, credit)

    def test_insufficient_stock_rolls_back(self):
        with self.assertRaises(Exception):
            create_sale(self.db, SalesInvoiceCreate(customer_id=self.customer.id, items=[{"product_id": self.product.id, "quantity": 1, "unit_price": 200}]), self.user.id)
        self.assertEqual(self.db.scalar(select(func.count()).select_from(StockMovement)), 0)


if __name__ == "__main__":
    unittest.main()
