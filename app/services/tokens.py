from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.invoices import (
    PurchaseInvoice,
    PurchaseInvoiceItem,
    SalesInvoice,
    SalesInvoiceItem,
)
from app.models.returns import (
    ReturnDocument,
    ReturnItem,
    ReturnType,
)
from app.models.token import (
    TokenClaim,
    TokenClaimStatus,
)
from app.services.governance import ensure_open_period
from app.services.invoices import (
    get_accounts,
    next_number,
    post_journal,
)

ZERO = Decimal("0")


def _whole(value: Any) -> Decimal:
    """
    Token quantities must always be whole numbers.
    """
    value = Decimal(str(value or 0))

    if value != value.to_integral_value():
        raise HTTPException(
            status_code=422,
            detail="Token quantities must be whole numbers",
        )

    return value.to_integral_value()


def _purchase_tokens(db: Session) -> Decimal:
    """
    Tokens received through posted purchases.

    Every quantity represents one token when the invoice
    line has token_included=True.
    """
    value = (
        db.scalar(
            select(
                func.coalesce(
                    func.sum(PurchaseInvoiceItem.quantity),
                    0,
                )
            )
            .join(
                PurchaseInvoice,
                PurchaseInvoice.id
                == PurchaseInvoiceItem.purchase_invoice_id,
            )
            .where(
                PurchaseInvoice.status == "posted",
                PurchaseInvoiceItem.token_included.is_(True),
            )
        )
        or ZERO
    )

    return _whole(value)


def _sale_tokens(
    db: Session,
    exclude_invoice_id=None,
) -> Decimal:
    """
    Tokens issued through posted sales.

    When validating a sale, the current invoice must be
    excluded because its token quantities are being validated
    before the sale is allowed to consume the inventory.
    """

    query = (
        select(
            func.coalesce(
                func.sum(SalesInvoiceItem.quantity),
                0,
            )
        )
        .join(
            SalesInvoice,
            SalesInvoice.id
            == SalesInvoiceItem.sales_invoice_id,
        )
        .where(
            SalesInvoice.status == "posted",
            SalesInvoiceItem.token_included.is_(True),
        )
    )

    if exclude_invoice_id is not None:
        query = query.where(
            SalesInvoice.id != exclude_invoice_id
        )

    value = db.scalar(query) or ZERO

    return _whole(value)


def _return_tokens(
    db: Session,
    return_type: ReturnType,
) -> Decimal:
    """
    Calculate tokens affected by returns.

    Purchase return:
        removes tokens that came in with the purchase.

    Sales return:
        restores tokens that were issued with the sale.
    """

    if return_type == ReturnType.PURCHASE_RETURN:
        source_model = PurchaseInvoiceItem
        source_join = (
            PurchaseInvoiceItem.id
            == ReturnItem.source_line_id
        )
    else:
        source_model = SalesInvoiceItem
        source_join = (
            SalesInvoiceItem.id
            == ReturnItem.source_line_id
        )

    value = (
        db.scalar(
            select(
                func.coalesce(
                    func.sum(ReturnItem.quantity),
                    0,
                )
            )
            .join(
                ReturnDocument,
                ReturnDocument.id
                == ReturnItem.return_document_id,
            )
            .join(
                source_model,
                source_join,
            )
            .where(
                ReturnDocument.return_type == return_type,
                source_model.token_included.is_(True),
            )
        )
        or ZERO
    )

    return _whole(value)


def token_inventory(db: Session) -> dict:
    """
    Return the complete token position.

    IMPORTANT:

    Available token inventory is:

        purchased
        - purchase returns
        - tokens issued through sales
        + sales returns

    Painter claims are NOT deducted from available inventory.

    Claims are tracked separately.
    """

    received = _purchase_tokens(db)

    purchase_returns = _return_tokens(
        db,
        ReturnType.PURCHASE_RETURN,
    )

    issued = _sale_tokens(db)

    sales_returns = _return_tokens(
        db,
        ReturnType.SALES_RETURN,
    )

    # Separate claim count.
    claimed = _whole(
        db.scalar(
            select(
                func.coalesce(
                    func.sum(TokenClaim.quantity),
                    0,
                )
            ).where(
                TokenClaim.status != TokenClaimStatus.VOID,
            )
        )
        or ZERO
    )

    # Total amount already reimbursed to painters.
    reimbursed_amount = (
        db.scalar(
            select(
                func.coalesce(
                    func.sum(TokenClaim.total_amount),
                    0,
                )
            ).where(
                TokenClaim.status == TokenClaimStatus.PAID,
            )
        )
        or ZERO
    )

    # --------------------------------------------------
    # MAIN TOKEN INVENTORY
    # --------------------------------------------------
    #
    # Claims are intentionally NOT included here.
    #
    available = (
        received
        - purchase_returns
        - issued
        + sales_returns
    )

    available = max(
        ZERO,
        available,
    )

    # --------------------------------------------------
    # SEPARATE CLAIMABLE POOL
    # --------------------------------------------------
    #
    # This represents tokens that have been issued through
    # sales but have not yet been claimed by painters.
    #
    claimable = (
        issued
        - sales_returns
        - claimed
    )

    claimable = max(
        ZERO,
        claimable,
    )

    return {
        "received": received,
        "purchase_return": purchase_returns,

        "issued": issued,
        "sales_return": sales_returns,

        # Physical/usable token inventory.
        "available": available,

        # Completely separate painter claim information.
        "claimed": claimed,
        "outstanding_claimable": claimable,
        "reimbursed_amount": Decimal(
            str(reimbursed_amount)
        ),

        "shortage": ZERO,
    }


def validate_token_line(
    quantity: Any,
    included: bool,
    value: Any,
) -> Decimal:
    """
    Validate token information on a purchase/sale line.
    """

    if not included:
        return ZERO

    quantity = _whole(quantity)

    if quantity <= ZERO:
        raise HTTPException(
            status_code=422,
            detail=(
                "Token-bearing quantity must be "
                "greater than zero"
            ),
        )

    token_value = Decimal(
        str(value or 0)
    )

    if token_value <= ZERO:
        raise HTTPException(
            status_code=422,
            detail=(
                "Token value must be greater than zero "
                "for a token-bearing line"
            ),
        )

    return quantity


def apply_invoice_tokens(
    db: Session,
    invoice_type: str,
    invoice_id,
    items: list[dict],
):
    """
    Apply manually selected token flags to invoice lines.

    Purchase:
        token-bearing lines increase token inventory.

    Sale:
        token-bearing lines consume token inventory.

    Claims never modify token inventory.
    """

    if invoice_type not in {
        "sale",
        "purchase",
    }:
        raise HTTPException(
            status_code=422,
            detail=(
                "invoice_type must be sale or purchase"
            ),
        )

    if invoice_type == "sale":
        model = SalesInvoiceItem
        fk = SalesInvoiceItem.sales_invoice_id
    else:
        model = PurchaseInvoiceItem
        fk = PurchaseInvoiceItem.purchase_invoice_id

    rows = {
        str(row.id): row
        for row in db.scalars(
            select(model).where(
                fk == invoice_id
            )
        ).all()
    }

    for item in items:
        row = rows.get(
            str(item["line_id"])
        )

        if not row:
            raise HTTPException(
                status_code=404,
                detail="Invoice line was not found",
            )

        included = bool(
            item.get(
                "token_included",
                False,
            )
        )

        if included:
            token_value = Decimal(
                str(
                    item.get(
                        "token_value",
                        0,
                    )
                )
            )
        else:
            token_value = ZERO

        validate_token_line(
            row.quantity,
            included,
            token_value,
        )

        row.token_included = included

        row.token_value = (
            token_value
            if included
            else ZERO
        )

    # --------------------------------------------------
    # SALE TOKEN VALIDATION
    # --------------------------------------------------
    #
    # A sale can only issue tokens that currently exist.
    #
    # Painter claims are NOT deducted from this number.
    #
    if invoice_type == "sale":
    # Tokens required by this sale.
        requested = sum(
            (
                _whole(row.quantity)
                for row in rows.values()
                if row.token_included
            ),
            ZERO,
        )

        # Calculate inventory BEFORE this sale.
        received = _purchase_tokens(db)

        purchase_returns = _return_tokens(
            db,
            ReturnType.PURCHASE_RETURN,
        )

        # IMPORTANT:
        # Exclude the current sale invoice from issued tokens.
        previously_issued = _sale_tokens(
            db,
            exclude_invoice_id=invoice_id,
        )

        sales_returns = _return_tokens(
            db,
            ReturnType.SALES_RETURN,
        )

        available_before_sale = (
            received
            - purchase_returns
            - previously_issued
            + sales_returns
        )

        available_before_sale = max(
            ZERO,
            available_before_sale,
        )

        if requested > available_before_sale:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Not enough tokens. "
                    f"This sale requires {requested} tokens, "
                    f"but only {available_before_sale} "
                    f"tokens are available."
                ),
            )

    db.commit()

    return token_inventory(db)


def create_claim(
    db: Session,
    payload,
    user_id,
):
    """
    Create a painter token claim.

    A claim is a separate reimbursement record.

    It DOES NOT reduce available token inventory.
    """

    ensure_open_period(
        db,
        payload.claim_date,
    )

    quantity = _whole(
        payload.quantity
    )

    if quantity <= ZERO:
        raise HTTPException(
            status_code=422,
            detail=(
                "Token claim quantity must be "
                "greater than zero"
            ),
        )

    token_value = Decimal(
        str(payload.token_value)
    )

    if token_value <= ZERO:
        raise HTTPException(
            status_code=422,
            detail=(
                "Token value must be greater than zero"
            ),
        )

    inventory = token_inventory(db)

    # Painter can only claim tokens that have actually
    # been issued through sales.
    if quantity > inventory["outstanding_claimable"]:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Only "
                f"{inventory['outstanding_claimable']} "
                "whole tokens are currently claimable"
            ),
        )

    total_amount = (
        quantity * token_value
    ).quantize(
        Decimal("0.01")
    )

    claim = TokenClaim(
        claim_number=next_number("TOK"),
        claim_date=payload.claim_date,
        painter_name=payload.painter_name,
        painter_phone=payload.painter_phone,
        quantity=quantity,
        token_value=token_value,
        total_amount=total_amount,
        notes=payload.notes,
        created_by_id=user_id,
        status=TokenClaimStatus.PENDING,
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    return claim


def pay_claim(
    db: Session,
    claim_id,
    method,
    user_id,
):
    """
    Pay a pending painter claim.

    This creates the accounting transaction but does NOT
    modify token inventory.
    """

    claim = db.get(
        TokenClaim,
        claim_id,
    )

    if not claim:
        raise HTTPException(
            status_code=404,
            detail="Token claim was not found",
        )

    if claim.status != TokenClaimStatus.PENDING:
        raise HTTPException(
            status_code=422,
            detail=(
                "Only a pending token claim "
                "can be paid"
            ),
        )

    accounts = get_accounts(
        db,
        "1000",
        "1010",
        "6000",
    )

    # Cash vs bank.
    cash_or_bank = (
        accounts["1010"]
        if method.value == "bank_transfer"
        else accounts["1000"]
    )

    entry = post_journal(
        db,
        entry_date=claim.claim_date,
        source_type="token_claim",
        source_id=str(claim.id),
        memo=(
            f"Painter token reimbursement "
            f"{claim.claim_number}"
        ),
        user_id=user_id,
        lines=[
            (
                accounts["6000"],
                claim.total_amount,
                ZERO,
                "Painter token reimbursement",
            ),
            (
                cash_or_bank,
                ZERO,
                claim.total_amount,
                "Token reimbursement payment",
            ),
        ],
    )

    claim.status = TokenClaimStatus.PAID
    claim.payment_method = method.value
    claim.journal_entry_id = entry.id

    db.commit()
    db.refresh(claim)

    return claim