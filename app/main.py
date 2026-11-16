from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from . import models, schemas
from .database import CORS_ORIGINS, Base, SessionLocal, engine, get_db
from .security import create_token, require_admin, verify_password
from .seed import seed_admin, seed_group_prices, seed_personal_prices, seed_plans


def _migrate() -> None:
    """Add columns introduced after the first release (create_all won't)."""
    with engine.begin() as conn:
        cols = {c["name"] for c in inspect(conn).get_columns("plans")}
        if "billing" not in cols:
            conn.execute(text(
                "ALTER TABLE plans ADD COLUMN billing VARCHAR(20) NOT NULL DEFAULT 'monthly'"
            ))
            conn.execute(text("UPDATE plans SET billing='one-time' WHERE unit='per session'"))


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    _migrate()
    with SessionLocal() as db:
        seed_plans(db)
        seed_admin(db)
        seed_personal_prices(db)
        seed_group_prices(db)
    yield


app = FastAPI(title="Mindful Minutes API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


# ---- Auth ----------------------------------------------------------------

@app.post("/api/admin/login", response_model=schemas.TokenOut)
def login(payload: schemas.LoginIn, db: Session = Depends(get_db)):
    admin = db.query(models.Admin).filter(models.Admin.email == payload.email).first()
    # Verify against a dummy hash when the email is unknown to keep timing similar.
    stored = admin.password_hash if admin else "scrypt$00$00"
    if not verify_password(payload.password, stored) or admin is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    return {"token": create_token(admin), "email": admin.email}


@app.get("/api/admin/me", dependencies=[Depends(require_admin)])
def me(admin: models.Admin = Depends(require_admin)):
    return {"email": admin.email}


# ---- Pricing -------------------------------------------------------------

@app.get("/api/plans", response_model=list[schemas.PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return db.query(models.Plan).order_by(models.Plan.position, models.Plan.id).all()


@app.post(
    "/api/plans",
    response_model=schemas.PlanOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_plan(payload: schemas.PlanCreate, db: Session = Depends(get_db)):
    plan = models.Plan(**payload.model_dump())
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _get_plan(db: Session, plan_id: int) -> models.Plan:
    plan = db.get(models.Plan, plan_id)
    if plan is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Plan not found")
    return plan


@app.patch(
    "/api/plans/{plan_id}",
    response_model=schemas.PlanOut,
    dependencies=[Depends(require_admin)],
)
def update_plan(plan_id: int, payload: schemas.PlanUpdate, db: Session = Depends(get_db)):
    plan = _get_plan(db, plan_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(plan, key, value)
    db.commit()
    db.refresh(plan)
    return plan


@app.delete(
    "/api/plans/{plan_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_plan(plan_id: int, db: Session = Depends(get_db)):
    db.delete(_get_plan(db, plan_id))
    db.commit()


# ---- Personal class prices ----------------------------------------------

_PERIOD_RANK = {"hour": 0, "week": 1, "month": 2}


def _get_price(db: Session, price_id: int) -> models.PersonalPrice:
    row = db.get(models.PersonalPrice, price_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Price not found")
    return row


def _ensure_unique(db: Session, mode: str, period: str, exclude_id: int | None = None):
    clash = (
        db.query(models.PersonalPrice)
        .filter_by(mode=mode, period=period)
        .filter(models.PersonalPrice.id != (exclude_id or 0))
        .first()
    )
    if clash:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A {mode} price per {period} already exists — edit it instead.",
        )


@app.get("/api/personal-prices", response_model=list[schemas.PersonalPriceOut])
def list_personal_prices(db: Session = Depends(get_db)):
    rows = db.query(models.PersonalPrice).all()
    return sorted(rows, key=lambda r: (r.mode, _PERIOD_RANK[r.period]))


@app.post(
    "/api/personal-prices",
    response_model=schemas.PersonalPriceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_personal_price(payload: schemas.PersonalPriceCreate, db: Session = Depends(get_db)):
    _ensure_unique(db, payload.mode, payload.period)
    row = models.PersonalPrice(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.patch(
    "/api/personal-prices/{price_id}",
    response_model=schemas.PersonalPriceOut,
    dependencies=[Depends(require_admin)],
)
def update_personal_price(
    price_id: int, payload: schemas.PersonalPriceUpdate, db: Session = Depends(get_db)
):
    row = _get_price(db, price_id)
    changes = payload.model_dump(exclude_unset=True)
    _ensure_unique(
        db, changes.get("mode", row.mode), changes.get("period", row.period), row.id
    )
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@app.delete(
    "/api/personal-prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_personal_price(price_id: int, db: Session = Depends(get_db)):
    db.delete(_get_price(db, price_id))
    db.commit()


# ---- Group class prices (online only) ------------------------------------

def _get_group_price(db: Session, price_id: int) -> models.GroupPrice:
    row = db.get(models.GroupPrice, price_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Price not found")
    return row


def _ensure_group_unique(db: Session, period: str, exclude_id: int | None = None):
    clash = (
        db.query(models.GroupPrice)
        .filter_by(period=period)
        .filter(models.GroupPrice.id != (exclude_id or 0))
        .first()
    )
    if clash:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"A group price per {period} already exists — edit it instead.",
        )


@app.get("/api/group-prices", response_model=list[schemas.GroupPriceOut])
def list_group_prices(db: Session = Depends(get_db)):
    rows = db.query(models.GroupPrice).all()
    return sorted(rows, key=lambda r: _PERIOD_RANK[r.period])


@app.post(
    "/api/group-prices",
    response_model=schemas.GroupPriceOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def create_group_price(payload: schemas.GroupPriceCreate, db: Session = Depends(get_db)):
    _ensure_group_unique(db, payload.period)
    row = models.GroupPrice(**payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@app.patch(
    "/api/group-prices/{price_id}",
    response_model=schemas.GroupPriceOut,
    dependencies=[Depends(require_admin)],
)
def update_group_price(
    price_id: int, payload: schemas.GroupPriceUpdate, db: Session = Depends(get_db)
):
    row = _get_group_price(db, price_id)
    changes = payload.model_dump(exclude_unset=True)
    _ensure_group_unique(db, changes.get("period", row.period), row.id)
    for key, value in changes.items():
        setattr(row, key, value)
    db.commit()
    db.refresh(row)
    return row


@app.delete(
    "/api/group-prices/{price_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_group_price(price_id: int, db: Session = Depends(get_db)):
    db.delete(_get_group_price(db, price_id))
    db.commit()


# ---- Contacts ------------------------------------------------------------

@app.post(
    "/api/contacts",
    response_model=schemas.ContactOut,
    status_code=status.HTTP_201_CREATED,
)
def create_contact(payload: schemas.ContactCreate, db: Session = Depends(get_db)):
    contact = models.Contact(**payload.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact


@app.get(
    "/api/contacts",
    response_model=list[schemas.ContactOut],
    dependencies=[Depends(require_admin)],
)
def list_contacts(db: Session = Depends(get_db)):
    return db.query(models.Contact).order_by(models.Contact.created_at.desc()).all()


@app.get(
    "/api/contacts/{contact_id}",
    response_model=schemas.ContactOut,
    dependencies=[Depends(require_admin)],
)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(models.Contact, contact_id)
    if contact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")
    return contact


@app.delete(
    "/api/contacts/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def delete_contact(contact_id: int, db: Session = Depends(get_db)):
    contact = db.get(models.Contact, contact_id)
    if contact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Contact not found")
    db.delete(contact)
    db.commit()
