from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from uuid import UUID

from app.api.v1.dependencies.auth import get_current_user
from app.infrastructure.database.session import get_session
from app.api.v1.schemas.subscriptions import TransactionCreate, TransactionResponse, UsageEventCreate, UsageEventResponse
from app.infrastructure.database.models.subscriptions import TransactionModel, UsageEventModel
from app.infrastructure.database.models.core import SubscriptionModel 

router = APIRouter()

async def verify_subscription_ownership(subscription_id: UUID, current_user_id: UUID, db: AsyncSession):
    query = select(SubscriptionModel).filter(SubscriptionModel.id == subscription_id)
    result = await db.execute(query)
    sub = result.scalars().first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="Subscription context not found")
    if sub.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-user write rejected.")
    return sub

@router.post("/{id}/transactions", response_model=TransactionResponse, status_code=201)
async def ingest_transaction(
    id: UUID, 
    payload: TransactionCreate, 
    current_user = Depends(get_current_user), 
    db: AsyncSession = Depends(get_session)
):
    await verify_subscription_ownership(id, current_user.id, db)
    
    if payload.external_id:
        query = select(TransactionModel).filter(TransactionModel.external_id == payload.external_id)
        result = await db.execute(query)
        existing = result.scalars().first()
        if existing: 
            return existing
            
    db_transaction = TransactionModel(
        subscription_id=id, 
        amount=payload.amount, 
        currency=payload.currency, 
        occurrence_time=payload.occurrence_time, 
        source=payload.source, 
        external_id=payload.external_id
    )
    db.add(db_transaction)
    await db.commit()
    await db.refresh(db_transaction)
    return db_transaction

@router.post("/usage-events", response_model=UsageEventResponse, status_code=201)
async def ingest_usage_event(
    payload: UsageEventCreate, 
    current_user = Depends(get_current_user), 
    db: AsyncSession = Depends(get_session)
):
    await verify_subscription_ownership(payload.subscription_id, current_user.id, db)
    
    if payload.idempotency_key:
        query = select(UsageEventModel).filter(UsageEventModel.idempotency_key == payload.idempotency_key)
        result = await db.execute(query)
        existing = result.scalars().first()
        if existing: 
            return existing
            
    units = payload.units_used
    is_unk = payload.is_unknown or (units is None)
    
    db_event = UsageEventModel(
        subscription_id=payload.subscription_id, 
        occurrence_time=payload.occurrence_time, 
        units_used=units, 
        is_unknown=is_unk, 
        source=payload.source, 
        idempotency_key=payload.idempotency_key
    )
    db.add(db_event)
    await db.commit()
    await db.refresh(db_event)
    return db_event
