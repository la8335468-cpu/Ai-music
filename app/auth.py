import firebase_admin
from firebase_admin import auth as firebase_auth, credentials
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.config import settings
from app.database import get_db
from app.models import User

bearer = HTTPBearer(auto_error=False)


def get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(settings.firebase_credentials)
        return firebase_admin.initialize_app(
            cred, {"projectId": settings.firebase_project_id}
        )


def get_current_user(
    token: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    if token is None:
        raise HTTPException(status_code=401, detail="Bearer token required")
    try:
        decoded = firebase_auth.verify_id_token(
            token.credentials, app=get_firebase_app(), check_revoked=True
        )
        provider = decoded.get("firebase", {}).get("sign_in_provider")
        if provider != "google.com":
            raise HTTPException(status_code=403, detail="Google Sign-In is required")
        uid = decoded["uid"]
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid, expired, or revoked Firebase token")

    user = db.get(User, uid)
    if user is None:
        user = User(
            id=uid,
            email=decoded.get("email"),
            display_name=decoded.get("name"),
            photo_url=decoded.get("picture"),
        )
        db.add(user)
    else:
        user.email = decoded.get("email")
        user.display_name = decoded.get("name")
        user.photo_url = decoded.get("picture")
    db.commit()
    db.refresh(user)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.id not in settings.admins:
        raise HTTPException(status_code=403, detail="Admin permission required")
    return user
