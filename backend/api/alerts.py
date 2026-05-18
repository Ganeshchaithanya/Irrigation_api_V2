from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List, Any
import uuid

from backend.db.session import get_db
from backend.app.dependencies import get_current_user
from backend.models.user import User
from backend.models.farm import Farm
from backend.models.state import FarmDiaryEntry # Using Diary as a general log for now or create Alert table

# Actually, let's create a real Alert model or use the existing service.
# For now, we'll implement a dedicated Alert model for better sync.

from backend.services.alerts import get_recent_alerts

router = APIRouter(prefix="/alerts", tags=["Notifications"])

@router.get("")
async def get_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 20
):
    """Fetch recent alerts for the user's farm."""
    # Find farm
    farm_res = await db.execute(select(Farm.id).where(Farm.user_id == current_user.id))
    farm_id = farm_res.scalars().first()
    if not farm_id:
        return []

    return await get_recent_alerts(str(farm_id), db, limit)
