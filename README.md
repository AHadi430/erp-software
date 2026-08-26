# Paint Shop ERP

Production-oriented ERP foundation for a single Pakistani paint retailer. The current milestone delivers a runnable FastAPI backend with PostgreSQL, JWT authentication, role-based access control, master data APIs, and the relational foundations for inventory and double-entry accounting.

## Start locally

1. Copy `.env.example` to `.env` and set a long `SECRET_KEY`.
2. Start PostgreSQL: `docker compose up -d db`.
3. Create a virtual environment, then run `pip install -r requirements.txt`.
4. Run `alembic upgrade head`.
5. Seed the initial administrator and Chart of Accounts: `python -m app.scripts.seed`.
6. Start the API: `uvicorn app.main:app --reload`.

Interactive API documentation is at `http://localhost:8000/docs`.

## Implemented API areas

- `/api/v1/auth` — login and current user
- `/api/v1/users` — user administration (admin only)
- `/api/v1/categories`, `/brands`, `/products`, `/customers`, `/suppliers`
- `/api/v1/sales` — post a sale with invoice items, stock issue, revenue/tax/COGS posting
- `/api/v1/purchases` — post a purchase with invoice items, stock receipt, inventory/tax/payable posting
- `/api/v1/sales/payments`, `/purchases/payments` — allocate receipts/payments to open invoices
- `/api/v1/sales/{id}/returns`, `/purchases/{id}/returns` — post inventory and ledger-backed returns
- `/api/v1/sales/{id}/cancel`, `/purchases/{id}/cancel` — reverse an unpaid, unreturned invoice safely
- `/api/v1/inventory/stock`, `/inventory/adjustments` — real-time quantity/value view and audited adjustments
- `/api/v1/reports` — dashboard KPIs, trial balance, P&L, balance sheet, receivables/payables, ledgers, and PDFs
- `/api/v1/settings` — single-shop business details and configurable tax rates

Sales and purchase invoices post as a single database unit: an error such as insufficient stock, an invalid payment, or an unbalanced journal entry rolls back the entire document. Payments and returns follow the same rule, including their allocations, stock movements, and accounting entries.

The React UI includes dashboard KPIs, sales and purchase entry, stock adjustment, and basic business/user administration. Run `npm install && npm run dev` from `frontend` after installing Node.js.

## Architecture

Business rules belong in `app/services`, HTTP endpoints in `app/api/routes`, ORM entities in `app/models`, and request/response contracts in `app/schemas`. Monetary columns are `NUMERIC`, inventory changes are immutable movements, and journal lines are constrained to balanced entries by the posting service.
