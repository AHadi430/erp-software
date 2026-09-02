from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user, require_roles
from app.database.session import get_db
from app.models.auth import User, UserRole
from app.models.operations import PaymentMethod
from app.models.token import TokenClaim
from app.schemas.token import TokenClaimCreate, TokenClaimRead
from app.services.tokens import apply_invoice_tokens, create_claim, pay_claim, token_inventory

router = APIRouter(prefix="/tokens", tags=["tokens"], dependencies=[Depends(get_current_user)])
accounting_access = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT))
write_access = Depends(require_roles(UserRole.ADMIN, UserRole.ACCOUNTANT, UserRole.INVENTORY_MANAGER, UserRole.SALESPERSON))

@router.get("/inventory")
def inventory(db: Session = Depends(get_db)):
    return token_inventory(db)

@router.post("/invoices/{invoice_type}/{invoice_id}", dependencies=[write_access])
def apply_invoice_token_flags(invoice_type: str, invoice_id: UUID, payload: dict, db: Session = Depends(get_db)):
    if invoice_type not in {"sale", "purchase"}:
        raise ValueError("invoice_type must be sale or purchase")
    return apply_invoice_tokens(db, invoice_type, invoice_id, payload.get("items", []))

@router.get("/claims", response_model=list[TokenClaimRead])
def claims(db: Session = Depends(get_db)):
    return list(db.scalars(select(TokenClaim).order_by(TokenClaim.claim_date.desc(), TokenClaim.created_at.desc())))

@router.post("/claims", response_model=TokenClaimRead, status_code=status.HTTP_201_CREATED, dependencies=[accounting_access])
def create_token_claim(payload: TokenClaimCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return create_claim(db, payload, user.id)

@router.post("/claims/{claim_id}/pay", response_model=TokenClaimRead, dependencies=[accounting_access])
def pay_token_claim(claim_id: UUID, method: PaymentMethod = PaymentMethod.CASH, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return pay_claim(db, claim_id, method, user.id)
