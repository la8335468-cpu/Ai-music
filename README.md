# ABHISHEK MUSIC — FastAPI Backend

This is a backend starter implementation. It includes:
- PostgreSQL + SQLAlchemy models and Alembic migration
- Firebase ID-token verification restricted to Google sign-in
- User identity synchronization
- Lifetime free reservation quota: 2 reservations per user
- Admin allowlist and authenticated admin APIs
- App enable/disable, maintenance and force-update settings
- Manual premium grants and subscription status
- Admin audit logs

## Important limitations

This does **not** generate music or lyrics and does not implement Google Play purchase verification, renewals, refunds, or payment webhooks. Manual premium grants are implemented. Actual audio generation requires a real AI music provider, worker/queue, storage, and provider credentials. Do not advertise those features as working until integrated and tested.

The free quota currently counts song reservations, not successful generated audio. Failed provider jobs still count. A production implementation should add a safe failure/refund policy and idempotency keys before connecting a provider.

## Local setup

Requires Python 3.11+ and PostgreSQL.

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` with real credentials. Never commit `.env` or service-account keys.

Run migrations:

```bash
alembic upgrade head
```

Run API:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Docs: http://127.0.0.1:8000/docs

## Firebase setup

1. Create a Firebase project.
2. Enable Google in Authentication > Sign-in method.
3. Register the Android package and configure SHA fingerprints.
4. Create/download a Firebase Admin service-account JSON securely.
5. Set `FIREBASE_PROJECT_ID` and `FIREBASE_SERVICE_ACCOUNT_JSON`.
6. Android must send a Firebase ID token as `Authorization: Bearer <ID_TOKEN>`.
7. Add your Firebase Auth UID to `ADMIN_UIDS` to authorize the admin account.

For multiple admins, comma-separate UIDs. Do not put admin UIDs in a client-side trust decision.

## Render deployment

Create a PostgreSQL database and a Python Web Service. Suggested settings:

- Root Directory: `.` (if this repository root is the Backend folder)
- Runtime: Python 3
- Build Command: `pip install -r requirements.txt`
- Pre-Deploy Command: `alembic upgrade head` (if available on your Render plan)
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

Set these Render environment variables:
- `PYTHON_VERSION` = `3.12.0`
- `ENVIRONMENT` = `production`
- `DATABASE_URL` = Render PostgreSQL Internal Database URL
- `FIREBASE_PROJECT_ID` = Firebase project ID
- `FIREBASE_SERVICE_ACCOUNT_JSON` = full service-account JSON as one environment-variable value
- `ADMIN_UIDS` = your Firebase Auth UID(s), comma-separated

If Pre-Deploy Command is unavailable, run `alembic upgrade head` once from Render Shell before relying on the service.

## Main endpoints

Public:
- `GET /`
- `GET /health`
- `GET /app/status`

Firebase Google-authenticated user:
- `GET /me`
- `GET /subscription/status`
- `GET /songs/quota`
- `POST /songs/reserve`

Admin (Firebase Google-authenticated UID must be in ADMIN_UIDS):
- `GET /admin/dashboard`
- `GET /admin/settings`
- `PATCH /admin/settings`
- `POST /admin/app/activate`
- `POST /admin/app/deactivate`
- `POST /admin/maintenance/enable`
- `POST /admin/maintenance/disable`
- `POST /admin/users/{uid}/premium`
- `GET /admin/users/{uid}/subscription`
- `GET /admin/audit`

## Security notes

- Keep credentials out of Git and Android source.
- Use HTTPS in production.
- Restrict CORS when adding Android/web clients.
- Add rate limiting, monitoring, backups, tests, and admin device enrollment before public launch.
- Admin UID allowlisting is server-side; the Android app alone is not a security boundary.
- The API status endpoint exposes app settings intentionally; do not expose secrets there.
