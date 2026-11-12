from datetime import datetime, timezone
from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models import User, SongRequest, Subscription

FREE_SONG_LIMIT = 2


def has_premium(db: Session, uid: str) -> bool:
    now = datetime.now(timezone.utc)
    rows = db.scalars(
        select(Subscription).where(
            Subscription.user_id == uid,
            Subscription.status == "active",
        )
    ).all()
    for row in rows:
        if row.expires_at is None:
            return True
        expiry = row.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry > now:
            return True
    return False


def reserve_song(db: Session, user: User) -> dict:
    try:
        # Locking the user row serializes quota reservations for this user on PostgreSQL.
        locked_user = db.scalar(
            select(User).where(User.id == user.id).with_for_update()
        )
        if locked_user is None:
            raise HTTPException(status_code=404, detail="User not found")

        premium = has_premium(db, user.id)
        used = db.scalar(
            select(func.count(SongRequest.id)).where(SongRequest.user_id == user.id)
        ) or 0
        if not premium and used >= FREE_SONG_LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "message": "Lifetime free-song limit reached",
                    "free_song_limit": FREE_SONG_LIMIT,
                    "used": used,
                    "upgrade_required": True,
                },
            )
        item = SongRequest(user_id=user.id, status="reserved")
        db.add(item)
        db.commit()
        db.refresh(item)
        return {
            "song_id": item.id,
            "status": item.status,
            "premium": premium,
            "note": "Reservation only; no audio has been generated.",
        }
    except Exception:
        db.rollback()
        raise
