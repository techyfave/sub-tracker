from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.future import select
from uuid import UUID
import json

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_session
from app.api.v1.schemas.subscriptions import TransactionCreate, UsageEventCreate
from app.infrastructure.database.models.core import SubscriptionModel, TransactionModel, UsageEventModel 

router = APIRouter()

async def get_validated_subscription(subscription_id: UUID, current_user_id: UUID, db: AsyncSession) -> SubscriptionModel:
    query = select(SubscriptionModel).filter(SubscriptionModel.id == subscription_id)
    result = await db.execute(query)
    sub = result.scalars().first()
    
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription context not found")
    if sub.user_id != current_user_id or getattr(sub, "is_deleted", False):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied: Resource ownership mismatch.")
    return sub

@router.post("/{id}/transactions", status_code=status.HTTP_201_CREATED)
async def ingest_transaction(
    id: UUID, 
    payload: TransactionCreate, 
    current_user = Depends(get_current_user), 
    db: AsyncSession = Depends(get_session)
):
    await get_validated_subscription(id, current_user.id, db)
    
    stmt = insert(TransactionModel).values(
        subscription_id=id,
        user_id=current_user.id,
        amount=payload.amount,
        currency=payload.currency,
        occurred_at=payload.occurrence_time,
        source=payload.source,
        external_reference=payload.external_reference
    )
    
    if payload.external_reference:
        stmt = stmt.on_conflict_do_update(
            index_elements=["external_reference"],
            set_={
                "amount": stmt.excluded.amount,
                "currency": stmt.excluded.currency
            }
        )
    
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "message": "Transaction ingestion completed successfully."}

@router.post("/usage-events", status_code=status.HTTP_201_CREATED)
async def ingest_usage_event(
    payload: UsageEventCreate, 
    current_user = Depends(get_current_user), 
    db: AsyncSession = Depends(get_session)
):
    await get_validated_subscription(payload.subscription_id, current_user.id, db)
    
    evidence_payload = {"source": payload.source, "is_unknown": payload.is_unknown}
    
    stmt = insert(UsageEventModel).values(
        subscription_id=payload.subscription_id,
        user_id=current_user.id,
        occurred_at=payload.occurrence_time,
        quantity=payload.quantity,
        evidence_json=json.dumps(evidence_payload),
        idempotency_key=payload.idempotency_key
    )
    
    if payload.idempotency_key:
        stmt = stmt.on_conflict_do_nothing(index_elements=["idempotency_key"])
        
    await db.execute(stmt)
    await db.commit()
    return {"status": "success", "message": "Usage metrics payload recorded successfully."}
