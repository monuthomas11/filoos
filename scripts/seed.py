"""Seed the FutureFunds database with realistic INR demo data.

Usage:
    python scripts/seed.py

Requires the virtual environment in backend/.venv to be active.
Migrations are applied automatically via Alembic on first run.
"""

from __future__ import annotations

import datetime
import sys
from decimal import Decimal
from pathlib import Path

# Ensure backend/ is importable.
_BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(_BACKEND))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: E402, F401 — register all models on Base.metadata
from app.config import get_settings  # noqa: E402
from app.crud.account import create_account  # noqa: E402
from app.crud.transaction import create_transaction, create_transfer  # noqa: E402
from app.models.account import AccountType  # noqa: E402
from app.schemas.account import AccountCreate  # noqa: E402


def _seed(db: Session) -> None:
    today = datetime.date.today()

    # ------------------------------------------------------------------
    # Accounts (4)
    # ------------------------------------------------------------------
    wallet = create_account(
        db,
        AccountCreate(
            name="Wallet",
            type=AccountType.CASH,
            currency="INR",
            opening_balance=Decimal("2500"),
        ),
    )
    hdfc = create_account(
        db,
        AccountCreate(
            name="HDFC Bank",
            type=AccountType.BANK,
            currency="INR",
            opening_balance=Decimal("45000"),
        ),
    )
    sbi = create_account(
        db,
        AccountCreate(
            name="SBI Savings",
            type=AccountType.SAVINGS,
            currency="INR",
            opening_balance=Decimal("120000"),
        ),
    )
    axis_cc = create_account(
        db,
        AccountCreate(
            name="Axis Credit Card",
            type=AccountType.CREDIT_CARD,
            currency="INR",
            opening_balance=Decimal("0"),
        ),
    )
    # Opening balance – credit card starts at -₹3,200
    create_transaction(
        db, axis_cc.id, Decimal("-3200"), "expense",
        "Opening balance", today - datetime.timedelta(days=30),
    )

    # ------------------------------------------------------------------
    # Transactions (10 rows ≈ 8 logical entries, two of which form a transfer)
    # ------------------------------------------------------------------
    # 1. Salary
    create_transaction(
        db, hdfc.id, Decimal("50000"), "income",
        "Monthly Salary", today - datetime.timedelta(days=10),
    )
    # 2. Rent
    create_transaction(
        db, hdfc.id, Decimal("-18000"), "expense",
        "Monthly Rent", today - datetime.timedelta(days=10),
    )
    # 3 → 4. Transfer to savings
    create_transfer(
        db, hdfc.id, sbi.id, Decimal("15000"),
        "Transfer to SBI Savings", today - datetime.timedelta(days=10),
    )
    # 5. Groceries
    create_transaction(
        db, wallet.id, Decimal("-1200"), "expense",
        "Groceries - BigBasket", today - datetime.timedelta(days=8),
    )
    # 6. Electricity bill
    create_transaction(
        db, hdfc.id, Decimal("-2400"), "expense",
        "Electricity Bill", today - datetime.timedelta(days=7),
    )
    # 7. Freelance income
    create_transaction(
        db, hdfc.id, Decimal("8000"), "income",
        "Freelance - Website project", today - datetime.timedelta(days=5),
    )
    # 8. Dinner
    create_transaction(
        db, axis_cc.id, Decimal("-850"), "expense",
        "Dinner - Barbeque Nation", today - datetime.timedelta(days=4),
    )
    # 9. Petrol
    create_transaction(
        db, axis_cc.id, Decimal("-2100"), "expense",
        "Petrol - HP Pump", today - datetime.timedelta(days=3),
    )
    # 10. Mobile recharge
    create_transaction(
        db, wallet.id, Decimal("-599"), "expense",
        "Jio Recharge", today - datetime.timedelta(days=1),
    )


def _ensure_migrations(engine) -> None:
    """Run ``alembic upgrade head`` so tables exist and are stamped."""
    import alembic.config
    import alembic.command

    alembic_cfg = alembic.config.Config(str(_BACKEND / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(_BACKEND / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    alembic.command.upgrade(alembic_cfg, "head")


def main() -> None:
    settings = get_settings()
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False},
    )
    _ensure_migrations(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, future=True)
    db = SessionLocal()
    try:
        _seed(db)
        print(f"[OK] Database seeded successfully ({settings.database_url})")
        print("   - 4 accounts: Wallet, HDFC Bank, SBI Savings, Axis Credit Card")
        print("   - 11 transaction rows (9 entries + 1 transfer = 2 rows)")
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    main()
