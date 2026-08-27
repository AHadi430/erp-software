from typing import Optional
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.auth import UserRole
from app.models.master import Brand, Category, Customer, Product, Supplier
from app.schemas.master import BrandCreate, BrandRead, CategoryCreate, CategoryRead, CustomerCreate, CustomerRead, ProductCreate, ProductRead, SupplierCreate, SupplierRead
from app.services.master import create_entity, list_entities, update_entity

write_access = Depends(require_roles(UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.SALESPERSON))
router = APIRouter(tags=["master data"])

def register_crud(prefix, model, create_schema, read_schema, search=False):
    subrouter = APIRouter(prefix=prefix)
    @subrouter.get("", response_model=list[read_schema], dependencies=[Depends(get_current_user)])
    def list_records(limit: int = 50, offset: int = 0, q: Optional[str] = None, db: Session = Depends(get_db)):
        return list_entities(db, model, min(max(limit, 1), 200), max(offset, 0), q if search else None)
    @subrouter.post("", response_model=read_schema, status_code=status.HTTP_201_CREATED, dependencies=[write_access])
    def create_record(payload: create_schema, db: Session = Depends(get_db)):
        return create_entity(db, model, payload)
    @subrouter.put("/{record_id}", response_model=read_schema, dependencies=[write_access])
    def update_record(record_id: str, payload: create_schema, db: Session = Depends(get_db)):
        return update_entity(db, model, record_id, payload)
    router.include_router(subrouter)

register_crud("/categories", Category, CategoryCreate, CategoryRead, True)
register_crud("/brands", Brand, BrandCreate, BrandRead, True)
register_crud("/products", Product, ProductCreate, ProductRead, True)
register_crud("/customers", Customer, CustomerCreate, CustomerRead, True)
register_crud("/suppliers", Supplier, SupplierCreate, SupplierRead, True)
