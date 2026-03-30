from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    severity: str,
    message: str,
    user_id: str | None = None,
    payload: dict | None = None,
) -> None:
    session.add(
        AuditEvent(
            event_type=event_type,
            severity=severity,
            message=message,
            user_id=user_id,
            payload=payload or {},
        )
    )

