# Mindful Minutes API

FastAPI backend for pricing plans and contact enquiries (SQLite).

## Setup
```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set ADMIN_API_KEY
fastapi dev app/main.py   # http://127.0.0.1:8000  (docs at /docs)
```

## Superadmin
`seed.py` creates one admin on first start from `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`
(if the password is blank, a random one is printed once in the server log).
Log in at `POST /api/admin/login` to get a bearer token (valid `TOKEN_HOURS`, default 12).
Set a long random `SECRET_KEY` so tokens survive restarts.

## Endpoints
| Method | Path | Auth |
|---|---|---|
| GET | /api/plans | public |
| POST / PATCH / DELETE | /api/plans[/{id}] | admin |
| POST | /api/contacts | public |
| GET | /api/contacts, /api/contacts/{id} | admin |
| DELETE | /api/contacts/{id} | admin |
| POST | /api/admin/login | public |
| GET | /api/admin/me | admin |
| GET | /api/health | public |

Plans have `billing`: `monthly`, `yearly` or `one-time`.
