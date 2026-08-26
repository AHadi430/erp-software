from __future__ import annotations

from decimal import Decimal
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models.master import Product
from app.models.operations import StockMovement, StockMovementType
from app.services.invoices import ZERO, get_accounts, money, next_number, post_journal

def inventory_snapshot(db: Session):
    quantities = dict(db.execute(select(StockMovement.product_id, func.coalesce(func.sum(StockMovement.quantity), 0)).group_by(StockMovement.product_id)).all())
    return [{"product_id": product.id, "sku": product.sku, "name": product.name, "quantity": quantity, "unit_cost": product.cost_price, "value": money(Decimal(quantity) * product.cost_price), "minimum_stock": product.minimum_stock, "is_low_stock": Decimal(quantity) <= product.minimum_stock} for product in db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.name)) for quantity in [Decimal(quantities.get(product.id, 0))]]

def adjust_stock(db: Session, payload, user_id):
    with db.begin_nested():
        product = db.scalar(select(Product).where(Product.id == payload.product_id, Product.is_active.is_(True)).with_for_update())
        if not product:
            raise HTTPException(status_code=404, detail="Active product was not found")
        current = Decimal(db.scalar(select(func.coalesce(func.sum(StockMovement.quantity), 0)).where(StockMovement.product_id == product.id)) or 0)
        if payload.quantity < 0 and current + payload.quantity < 0:
            raise HTTPException(status_code=422, detail="Adjustment would make stock negative")
        unit_cost = payload.unit_cost if payload.unit_cost is not None else product.cost_price
        amount = money(abs(payload.quantity) * unit_cost)
        accounts = get_accounts(db, "1200", "4100", "5100")
        if payload.quantity > 0:
            lines = [(accounts["1200"], amount, ZERO, "Inventory adjustment in"), (accounts["4100"], ZERO, amount, "Inventory adjustment gain")]
        else:
            lines = [(accounts["5100"], amount, ZERO, "Inventory adjustment loss"), (accounts["1200"], ZERO, amount, "Inventory adjustment out")]
        movement = StockMovement(product_id=product.id, movement_type=StockMovementType.ADJUSTMENT, quantity=payload.quantity, unit_cost=unit_cost, reference_type="stock_adjustment", reference_id=next_number("ADJ"), notes=payload.notes, created_by_id=user_id)
        db.add(movement); db.flush()
        post_journal(db, entry_date=movement.occurred_on, source_type="stock_adjustment", source_id=str(movement.id), memo=payload.notes, user_id=user_id, lines=lines)
    db.commit(); db.refresh(movement)
    return movement
