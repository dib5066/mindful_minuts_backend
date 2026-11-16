from sqlalchemy.orm import Session

import secrets

from .database import ADMIN_EMAIL, ADMIN_PASSWORD
from .models import Admin, GroupPrice, PersonalPrice, Plan
from .security import hash_password

# Placeholder prices (INR) — mirror the pricing page; edit via the API.
DEFAULT_PLANS = [
    dict(
        category="Personal Yoga", name="Single session", price=1500,
        unit="per session",
        description="Try one-to-one guidance with no commitment.",
        features=[
            "60-minute private session",
            "Practice shaped around your goals",
            "Breathing and mindfulness guidance",
        ],
        href="/personal-yoga", cta="Book personal yoga", billing="one-time", featured=False, position=1,
    ),
    dict(
        category="Personal Yoga", name="Monthly personal", price=10000,
        unit="per month · 8 sessions",
        description="Build a steady, personalised practice over time.",
        features=[
            "8 private sessions a month",
            "Custom plan that adapts as you grow",
            "Flexible scheduling",
            "Support between sessions on WhatsApp",
        ],
        href="/personal-yoga", cta="Start personal yoga", billing="monthly", featured=True, position=2,
    ),
    dict(
        category="Group Classes", name="Group monthly", price=3000,
        unit="per month · 12 classes",
        description="Practise alongside others in a supportive space.",
        features=[
            "12 group classes a month",
            "Suitable for all experience levels",
            "Build consistency with community",
        ],
        href="/group-classes", cta="Join group classes", billing="monthly", featured=False, position=3,
    ),
]


def seed_plans(db: Session) -> None:
    if db.query(Plan).first() is None:
        db.add_all(Plan(**p) for p in DEFAULT_PLANS)
        db.commit()


def seed_admin(db: Session) -> None:
    """Create the single superadmin if none exists."""
    if db.query(Admin).first() is not None:
        return
    password = ADMIN_PASSWORD or secrets.token_urlsafe(12)
    db.add(Admin(email=ADMIN_EMAIL, password_hash=hash_password(password)))
    db.commit()
    if not ADMIN_PASSWORD:
        print(f"[seed] Superadmin created: {ADMIN_EMAIL} / {password}  (set ADMIN_PASSWORD to choose your own)")


def seed_personal_prices(db: Session) -> None:
    # Placeholder rates (INR) — edit from the superadmin.
    if db.query(PersonalPrice).first() is None:
        db.add_all([
            PersonalPrice(mode="online", period="hour", price=1200),
            PersonalPrice(mode="offline", period="hour", price=1800),
        ])
        db.commit()


def seed_group_prices(db: Session) -> None:
    # Placeholder rate (INR) — edit from the superadmin.
    if db.query(GroupPrice).first() is None:
        db.add(GroupPrice(period="month", price=3000, note="12 classes"))
        db.commit()
