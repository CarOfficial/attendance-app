# Attendance API (backend)

FastAPI + PostgreSQL. Handles authentication, employee and branch management, and geofenced check-in/out.

## Run locally (SQLite, no Docker)

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

export DATABASE_URL=sqlite:///./dev.db
export JWT_SECRET=dev-secret-dev-secret-dev-secret-1234
export ADMIN_BOOTSTRAP_PASSWORD=Dev-Admin-Pass-1

uvicorn app.main:app --reload
# API docs: http://127.0.0.1:8000/docs
```

## Tests

```bash
pytest -q
```

## Production (Docker)

```bash
cp backend/.env.example backend/.env   # edit every CHANGE_ME value
echo "DB_PASSWORD=..." > .env          # same password as in DATABASE_URL
docker compose up -d --build
```

The API listens on `127.0.0.1:8000`. Put a reverse proxy with HTTPS (Caddy or Nginx) in front of it.

## Main rules

- **Login:** username + password. Usernames are unique (case-insensitive). An admin sets the initial password. The employee must change it on first login.
- **Lockout:** after 5 failed attempts the account is locked for 15 minutes.
- **Token revocation:** changing or resetting a password, or deactivating an account, invalidates existing tokens.
- **Check-in:** the server checks GPS accuracy (max 100 m by default) and the distance to each assigned active branch (its radius). Only one check-in per day.
- **Check-out:** must be within the radius of the branch where the employee checked in.
- **Time:** stored in UTC. The work day is computed in `TIMEZONE` (default `Asia/Tehran`).

## Layout

```
app/
  main.py          app factory, lifespan (create tables, bootstrap admin), routers
  config.py        settings from environment variables
  models.py        User, Branch, AttendanceRecord
  schemas.py       request/response models and validation
  security.py      bcrypt hashing, JWT
  deps.py          auth dependencies (current user, ready user, admin)
  geo.py           haversine distance
  services/        attendance business logic
  routers/         auth, admin, attendance endpoints
tests/             pytest suite (SQLite)
```
