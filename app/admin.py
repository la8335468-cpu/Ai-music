import json
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth import require_admin
from app.models import User, AppSetting, Subscription, AuditLog, SongRequest
from app.schemas import AppSettingsUpdate, PremiumGrantRequest

router = APIRouter(prefix="/admin", tags=["Master Admin"])


def get_settings(db: Session) -> AppSetting:
    settings_row = db.get(AppSetting, 1)
    if settings_row is None:
        settings_row = AppSetting(id=1)
        db.add(settings_row)
        db.flush()
    return settings_row


def audit(db: Session, admin_uid: str, action: str, target=None, details=None):
    db.add(AuditLog(
        admin_uid=admin_uid,
        action=action,
        target=target,
        details=json.dumps(details or {}, separators=(",", ":")),
    ))


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s = get_settings(db)
    result = {
        "project": "ABHISHEK MUSIC",
        "admin_uid": admin.id,
        "total_users": db.scalar(select(func.count(User.id))) or 0,
        "total_song_reservations": db.scalar(select(func.count(SongRequest.id))) or 0,
        "app_enabled": s.app_enabled,
        "maintenance_mode": s.maintenance_mode,
    }
    db.commit()
    return result


@router.get("/settings")
def read_settings(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s = get_settings(db)
    result = {
        "app_enabled": s.app_enabled,
        "maintenance_mode": s.maintenance_mode,
        "force_update": s.force_update,
        "minimum_version": s.minimum_version,
        "update_message": s.update_message,
    }
    db.commit()
    return result


@router.patch("/settings")
def update_settings(payload: AppSettingsUpdate, db: Session = Depends(get_db),
                    admin: User = Depends(require_admin)):
    s = get_settings(db)
    changes = payload.model_dump(exclude_unset=True)
    for key, value in changes.items():
        setattr(s, key, value)
    audit(db, admin.id, "APP_SETTINGS_UPDATED", details=changes)
    db.commit()
    return {"success": True, "settings": changes}


@router.post("/app/activate")
def activate_app(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s = get_settings(db)
    s.app_enabled = True
    audit(db, admin.id, "APP_ACTIVATED")
    db.commit()
    return {"success": True, "app_enabled": True}


@router.post("/app/deactivate")
def deactivate_app(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s = get_settings(db)
    s.app_enabled = False
    audit(db, admin.id, "APP_DEACTIVATED")
    db.commit()
    return {"success": True, "app_enabled": False}


@router.post("/maintenance/enable")
def maintenance_enable(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s = get_settings(db)
    s.maintenance_mode = True
    audit(db, admin.id, "MAINTENANCE_ENABLED")
    db.commit()
    return {"success": True, "maintenance_mode": True}


@router.post("/maintenance/disable")
def maintenance_disable(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    s = get_settings(db)
    s.maintenance_mode = False
    audit(db, admin.id, "MAINTENANCE_DISABLED")
    db.commit()
    return {"success": True, "maintenance_mode": False}


@router.post("/users/{uid}/premium")
def grant_premium(uid: str, payload: PremiumGrantRequest,
                 db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    if db.get(User, uid) is None:
        raise HTTPException(status_code=404, detail="User not found")
    now = datetime.now(timezone.utc)
    expires = {
        "monthly": now + timedelta(days=30),
        "yearly": now + timedelta(days=365),
        "lifetime": None,
    }[payload.plan]
    sub = Subscription(
        user_id=uid, plan=payload.plan, status="active",
        source="admin", granted_by=admin.id, expires_at=expires,
    )
    db.add(sub)
    audit(db, admin.id, "PREMIUM_GRANTED", target=uid,
          details={"plan": payload.plan, "reason": payload.reason})
    db.commit()
    return {
        "success": True, "user_id": uid, "plan": payload.plan,
        "expires_at": expires.isoformat() if expires else None,
    }


@router.get("/users/{uid}/subscription")
def subscription_history(uid: str, db: Session = Depends(get_db),
                         admin: User = Depends(require_admin)):
    if db.get(User, uid) is None:
        raise HTTPException(status_code=404, detail="User not found")
    rows = db.scalars(
        select(Subscription).where(Subscription.user_id == uid)
        .order_by(desc(Subscription.created_at))
    ).all()
    return [{
        "id": x.id, "plan": x.plan, "status": x.status, "source": x.source,
        "expires_at": x.expires_at.isoformat() if x.expires_at else None,
    } for x in rows]


@router.get("/audit")
def audit_history(limit: int = Query(default=100, ge=1, le=500),
                  db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    rows = db.scalars(select(AuditLog).order_by(desc(AuditLog.created_at)).limit(limit)).all()
    return [{
        "id": x.id, "admin_uid": x.admin_uid, "action": x.action,
        "target": x.target, "details": x.details,
        "created_at": x.created_at.isoformat(),
    } for x in rows]
