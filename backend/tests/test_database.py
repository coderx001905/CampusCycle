from datetime import datetime, timezone
from pathlib import Path
import os
import sqlite3
import subprocess
import sys

import pytest
from sqlalchemy import create_engine, event, inspect, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import create_database_engine
from app.models import Base, College, RefreshToken, Request, Resource, Transfer, TransferStatusHistory, User


@pytest.fixture
def db_engine(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'models.db'}")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def college(name: str, *, status: str = "verified") -> College:
    return College(
        name=name,
        address="1 Campus Road",
        city="Test City",
        contact_email=f"{name.lower().replace(' ', '.')}@example.edu",
        verification_status=status,
    )


def add_valid_graph(session: Session):
    source = college("Source College")
    destination = college("Destination College")
    session.add_all([source, destination])
    session.flush()
    source_rep = User(
        college=source, name="Source Rep", email="source@example.edu",
        password_hash="hash", role="college_representative",
    )
    destination_rep = User(
        college=destination, name="Destination Rep", email="destination@example.edu",
        password_hash="hash", role="college_representative",
    )
    source_rep_two = User(
        college=source, name="Source Rep Two", email="source-two@example.edu",
        password_hash="hash", role="college_representative",
    )
    admin = User(name="Admin", email="admin@example.edu", password_hash="hash", role="platform_admin")
    session.add_all([source_rep, source_rep_two, destination_rep, admin])
    session.flush()
    offered = Resource(
        college=source, created_by=source_rep, name="Offered books", category="Books",
        condition="Used", quantity_total=10, quantity_available=10, quantity_reserved=0,
        unit="books", transfer_type="exchange", status="active",
    )
    requested = Resource(
        college=destination, created_by=destination_rep, name="Requested desks", category="Furniture",
        condition="Good", quantity_total=5, quantity_available=5, quantity_reserved=0,
        unit="pieces", transfer_type="donation", status="active",
    )
    offered_extra = Resource(
        college=source, created_by=source_rep, name="Extra books", category="Books",
        condition="Used", quantity_total=4, quantity_available=4, quantity_reserved=0,
        unit="books", transfer_type="donation", status="active",
    )
    session.add_all([offered, requested, offered_extra])
    session.flush()
    req = Request(
        resource=requested, offered_resource=offered, requesting_college=source,
        requested_by=source_rep, reviewed_by=destination_rep,
        requested_quantity=2, offered_quantity=3, request_type="exchange", status="pending", purpose="Classroom setup",
    )
    session.add(req)
    session.flush()
    transfer = Transfer(
        request=req, resource=requested, transfer_leg="requested_resource",
        source_college=destination, destination_college=source, quantity=2,
        created_by=destination_rep, status="preparing", dispute_status="none",
    )
    session.add(transfer)
    session.flush()
    replacement = Transfer(
        request=req, resource=requested, transfer_leg="requested_resource",
        source_college=destination, destination_college=source, quantity=1,
        created_by=destination_rep, status="preparing", dispute_status="none", replacement_for=transfer,
    )
    session.add_all([
        replacement,
        TransferStatusHistory(transfer=transfer, changed_by=destination_rep, actor_type="user", new_status="preparing"),
        TransferStatusHistory(transfer=transfer, actor_type="system", previous_status="preparing", new_status="dispatched"),
    ])
    old_token = RefreshToken(
        user=source_rep, token_hash="hash-1", jti="jti-1", token_family_id="family-1",
        expires_at=datetime.now(timezone.utc),
    )
    next_token = RefreshToken(
        user=source_rep, token_hash="hash-2", jti="jti-2", token_family_id="family-1",
        expires_at=datetime.now(timezone.utc),
    )
    old_token.replaced_by = next_token
    session.add_all([old_token, next_token])
    session.flush()
    return source, destination, source_rep, destination_rep, req, transfer, replacement, old_token, next_token


def test_metadata_contains_exactly_seven_approved_business_tables() -> None:
    assert set(Base.metadata.tables) == {
        "colleges", "users", "resources", "requests", "transfers",
        "transfer_status_history", "refresh_tokens",
    }


def test_all_relationships_and_utc_timestamp_normalization(db_engine) -> None:
    with Session(db_engine) as session:
        source, destination, source_rep, destination_rep, req, transfer, replacement, old_token, next_token = add_valid_graph(session)
        session.commit()
        session.expire_all()

        loaded_source = session.scalar(select(College).where(College.id == source.id))
        loaded_request = session.scalar(select(Request).where(Request.id == req.id))
        loaded_transfer = session.scalar(select(Transfer).where(Transfer.id == transfer.id))
        loaded_token = session.scalar(select(RefreshToken).where(RefreshToken.id == old_token.id))
        assert len(loaded_source.users) == 2
        assert len(loaded_source.resources) == 2
        assert loaded_source.resources[0].created_by.id == source_rep.id
        assert loaded_request.resource.college_id == destination.id
        assert loaded_request.offered_resource.college_id == source.id
        assert loaded_request.requested_by.id == source_rep.id
        assert loaded_request.reviewed_by.id == destination_rep.id
        assert len(loaded_request.transfers) == 2
        assert loaded_transfer.source_college_id == destination.id
        assert loaded_transfer.destination_college_id == source.id
        assert loaded_transfer.replacement_transfers[0].id == replacement.id
        assert len(loaded_transfer.status_history) == 2
        assert loaded_token.user.id == source_rep.id
        assert loaded_token.replaced_by.id == next_token.id
        assert loaded_token.expires_at.tzinfo == timezone.utc


def test_case_insensitive_email_uniqueness_and_role_college_rules(db_engine) -> None:
    with Session(db_engine) as session:
        c = college("One")
        session.add(c)
        session.flush()
        session.add(User(college=c, name="Rep", email="Case@Example.edu", password_hash="x", role="college_representative"))
        session.commit()
        session.add(User(college=c, name="Rep 2", email="case@example.edu", password_hash="x", role="college_representative"))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        session.add(User(college=c, name="Bad Admin", email="admin-bad@example.edu", password_hash="x", role="platform_admin"))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
        session.add(User(name="Bad Rep", email="rep-bad@example.edu", password_hash="x", role="college_representative"))
        with pytest.raises(IntegrityError):
            session.flush()


@pytest.mark.parametrize("status", ["unverified", "approved"])
def test_invalid_college_verification_status_rejected(db_engine, status) -> None:
    with Session(db_engine) as session:
        session.add(college("Invalid", status=status))
        with pytest.raises(IntegrityError):
            session.flush()


@pytest.mark.parametrize(
    "values",
    [
        {"quantity_total": -1, "quantity_available": 0, "quantity_reserved": 0},
        {"quantity_total": 4, "quantity_available": 2, "quantity_reserved": 1},
        {"quantity_total": 3, "quantity_available": 1, "quantity_reserved": 4},
    ],
)
def test_invalid_resource_quantities_rejected(db_engine, values) -> None:
    with Session(db_engine) as session:
        c = college("College")
        session.add(c)
        session.flush()
        user = User(college=c, name="Rep", email="rep@example.edu", password_hash="x", role="college_representative")
        session.add(user)
        session.flush()
        session.add(Resource(
            college=c, created_by=user, name="Item", category="Other", condition="Flexible",
            unit="pieces", transfer_type="donation", **values,
        ))
        with pytest.raises(IntegrityError):
            session.flush()


def test_invalid_request_types_quantities_and_exchange_fields_rejected(db_engine) -> None:
    with Session(db_engine) as session:
        _, _, _, _, req, *_ = add_valid_graph(session)
        req.requested_quantity = 0
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        _, _, _, _, req, *_ = add_valid_graph(session)
        req.request_type = "temporary_borrowing"
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        _, _, _, _, req, *_ = add_valid_graph(session)
        req.status = "reopened"
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        _, _, _, _, req, *_ = add_valid_graph(session)
        req.request_type = "donation"
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        _, _, _, _, req, *_ = add_valid_graph(session)
        req.offered_resource_id = None
        req.offered_quantity = None
        with pytest.raises(IntegrityError):
            session.flush()


def test_invalid_transfer_fields_receipt_totals_and_history_actor_rejected(db_engine) -> None:
    with Session(db_engine) as session:
        *_, transfer, _, _, _ = add_valid_graph(session)
        transfer.quantity_received_good = transfer.quantity + 1
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        *_, transfer, _, _, _ = add_valid_graph(session)
        transfer.status = "in_transit"
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        *_, transfer, _, _, _ = add_valid_graph(session)
        transfer.transfer_leg = "return"
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        *_, transfer, _, _, _ = add_valid_graph(session)
        transfer.quantity = 0
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        *_, transfer, _, _, _ = add_valid_graph(session)
        transfer.dispute_status = "ignored"
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        *_, transfer, _, _, _ = add_valid_graph(session)
        session.add(TransferStatusHistory(transfer=transfer, actor_type="automation", new_status="preparing"))
        with pytest.raises(IntegrityError):
            session.flush()


def test_refresh_token_uniqueness_and_restrict_delete(db_engine) -> None:
    with Session(db_engine) as session:
        source, _, source_rep, _, _, _, _, token, _ = add_valid_graph(session)
        session.add(RefreshToken(
            user=source_rep, token_hash=token.token_hash, jti="jti-duplicate-hash",
            token_family_id="another-family", expires_at=datetime.now(timezone.utc),
        ))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        source, _, source_rep, _, _, _, _, _, _ = add_valid_graph(session)
        session.add(RefreshToken(
            user=source_rep, token_hash="unique-hash", jti="jti-1",
            token_family_id="another-family", expires_at=datetime.now(timezone.utc),
        ))
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()

        source, *_ = add_valid_graph(session)
        session.delete(source)
        with pytest.raises(IntegrityError):
            session.flush()


def test_invalid_foreign_keys_are_rejected(db_engine) -> None:
    with Session(db_engine) as session:
        session.add(User(college_id=999, name="Rep", email="rep@example.edu", password_hash="x", role="college_representative"))
        with pytest.raises(IntegrityError):
            session.flush()


def test_utc_datetime_normalizes_naive_and_offset_values(db_engine) -> None:
    with Session(db_engine) as session:
        c = college("UTC")
        c.created_at = datetime(2026, 1, 1, 12)
        session.add(c)
        session.commit()
        session.refresh(c)
        assert c.created_at == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


def test_initial_alembic_migration_on_isolated_sqlite_database(tmp_path) -> None:
    database = tmp_path / "migration.sqlite3"
    backend_dir = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["CC_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr

    inspector_engine = create_database_engine(env["CC_DATABASE_URL"])
    try:
        inspector = inspect(inspector_engine)
        assert set(inspector.get_table_names()) == set(Base.metadata.tables) | {"alembic_version"}
        for table, column in (
            ("resources", "status"),
            ("requests", "status"),
            ("transfers", "status"),
            ("transfers", "dispute_status"),
        ):
            assert next(
                item["default"]
                for item in inspector.get_columns(table)
                if item["name"] == column
            ) is None
        for table in Base.metadata.tables:
            if table != "colleges":
                assert inspector.get_foreign_keys(table)
        with inspector_engine.connect() as connection:
            email_index = connection.exec_driver_sql(
                "SELECT sql FROM sqlite_master WHERE type='index' AND name='uq_users_email_lower'"
            ).scalar_one()
            assert "lower(email)" in email_index.lower()
            index_names = {
                row[0]
                for row in connection.exec_driver_sql(
                    "SELECT name FROM sqlite_master WHERE type='index'"
                )
            }
            assert "ix_users_college_id_is_active" in index_names
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    finally:
        inspector_engine.dispose()
