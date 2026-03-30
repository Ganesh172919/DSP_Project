from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.models import AuthenticationAttempt, User
from app.schemas.auth import UserProfileResponse

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    email: str = Query(...),
    session: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    attempts = list(
        (
            await session.scalars(
                select(AuthenticationAttempt)
                .where(AuthenticationAttempt.user_id == user.id)
                .order_by(desc(AuthenticationAttempt.created_at))
                .limit(10)
            )
        ).all()
    )
    return UserProfileResponse(
        full_name=user.full_name,
        email=user.email,
        registration_completed=user.registration_completed,
        template_quality_score=user.template_quality_score,
        security_score=user.security_score,
        recent_attempts=[
            {
                "id": attempt.id,
                "status": attempt.status,
                "final_score": attempt.final_score,
                "created_at": attempt.created_at.isoformat(),
            }
            for attempt in attempts
        ],
    )

