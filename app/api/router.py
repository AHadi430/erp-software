from fastapi import APIRouter
from app.api.routes import auth, invoices, master, operations, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(master.router)
api_router.include_router(invoices.sales_router)
api_router.include_router(invoices.purchases_router)
api_router.include_router(operations.inventory_router)
api_router.include_router(operations.reports_router)
api_router.include_router(operations.settings_router)
