from pathlib import Path
import os
import subprocess
import sys

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import create_database_engine
from app.models import Base, College, Request, Resource, User


@pytest.fixture
def db_engine(tmp_path):
    engine = create_database_engine(f"sqlite:///{tmp_path / 'request-integrity.sqlite3'}")
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def _request(
    session: Session,
    *,
    request_type: str,
    offered_resource: Resource | None,
    offered_quantity: int | None,
) -> Request:
    college = College(
        name="Test College", address="1 Campus Road", city="Test City",
        contact_email="college@example.edu", verification_status="verified",
    )
    session.add(college)
    session.flush()
    user = User(
        college=college, name="Representative", email="rep@example.edu",
        password_hash="test-hash", role="college_representative",
    )
    resource = Resource(
        college=college, created_by=user, name="Requested Resource", category="Books",
        condition="Used", quantity_total=10, quantity_available=10, quantity_reserved=0,
        unit="pieces", transfer_type="donation", status="active",
    )
    session.add_all([user, resource])
    session.flush()
    return Request(
        resource=resource,
        requesting_college=college,
        requested_by=user,
        offered_resource=offered_resource,
        requested_quantity=1,
        offered_quantity=offered_quantity,
        request_type=request_type,
        purpose="Database constraint regression case",
        status="pending",
    )


@pytest.mark.parametrize(
    ("request_type", "offer_present", "offered_quantity", "accepted"),
    [
        ("exchange", True, 2, True),
        ("exchange", True, None, False),
        ("exchange", True, 0, False),
        ("exchange", False, 2, False),
        ("donation", False, None, True),
        ("donation", True, 2, False),
        ("purchase_enquiry", False, None, True),
        ("purchase_enquiry", True, 2, False),
    ],
)
def test_request_offer_fields_are_enforced_by_sqlite(
    db_engine, request_type, offer_present, offered_quantity, accepted
) -> None:
    with Session(db_engine) as session:
        college = College(
            name="Offering College", address="2 Campus Road", city="Test City",
            contact_email="offering@example.edu", verification_status="verified",
        )
        session.add(college)
        session.flush()
        offering_user = User(
            college=college, name="Offering Representative", email="offering-rep@example.edu",
            password_hash="test-hash", role="college_representative",
        )
        offered_resource = Resource(
            college=college, created_by=offering_user, name="Offered Resource", category="Books",
            condition="Used", quantity_total=5, quantity_available=5, quantity_reserved=0,
            unit="pieces", transfer_type="exchange", status="active",
        )
        session.add_all([offering_user, offered_resource])
        session.flush()

        request = _request(
            session,
            request_type=request_type,
            offered_resource=offered_resource if offer_present else None,
            offered_quantity=offered_quantity,
        )
        session.add(request)
        if accepted:
            session.flush()
            assert request.id is not None
        else:
            with pytest.raises(IntegrityError):
                session.flush()
            session.rollback()


def _run_alembic(backend_dir: Path, database: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CC_DATABASE_URL"] = f"sqlite:///{database.as_posix()}"
    return subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=backend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _seed_previous_head_records(database_url: str) -> None:
    engine = create_database_engine(database_url)
    try:
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO colleges (id, name, address, city, contact_email, verification_status) "
                "VALUES (1, 'Existing College', '1 Campus Road', 'Test City', 'existing@example.edu', 'verified')"
            ))
            connection.execute(text(
                "INSERT INTO users (id, college_id, name, email, password_hash, role, is_active) "
                "VALUES (1, 1, 'Existing Rep', 'existing-rep@example.edu', 'hash', 'college_representative', 1)"
            ))
            connection.execute(text(
                "INSERT INTO resources (id, college_id, created_by_user_id, name, category, condition, "
                "quantity_total, quantity_available, quantity_reserved, unit, transfer_type, status) "
                "VALUES (1, 1, 1, 'Existing Books', 'Books', 'Used', 8, 8, 0, 'pieces', 'exchange', 'active')"
            ))
            connection.execute(text(
                "INSERT INTO requests (id, resource_id, requesting_college_id, requested_by_user_id, "
                "offered_resource_id, requested_quantity, offered_quantity, request_type, purpose, status) "
                "VALUES (1, 1, 1, 1, 1, 2, 3, 'exchange', 'Existing valid exchange', 'pending')"
            ))
            connection.execute(text(
                "INSERT INTO requests (id, resource_id, requesting_college_id, requested_by_user_id, "
                "offered_resource_id, requested_quantity, offered_quantity, request_type, purpose, status) "
                "VALUES (2, 1, 1, 1, NULL, 1, NULL, 'donation', 'Existing donation request', 'pending')"
            ))
            connection.execute(text(
                "INSERT INTO transfers (id, request_id, resource_id, transfer_leg, source_college_id, "
                "destination_college_id, quantity, dispute_status, created_by_user_id, status) "
                "VALUES (1, 1, 1, 'requested_resource', 1, 1, 1, 'none', 1, 'preparing')"
            ))
            connection.execute(text(
                "INSERT INTO transfer_status_history (id, transfer_id, actor_type, new_status) "
                "VALUES (1, 1, 'system', 'preparing')"
            ))
            connection.execute(text(
                "INSERT INTO refresh_tokens (id, user_id, token_hash, jti, token_family_id, expires_at) "
                "VALUES (1, 1, 'existing-token-hash', 'existing-jti', 'existing-family', '2030-01-01 00:00:00')"
            ))
    finally:
        engine.dispose()


def test_corrective_migration_from_previous_head_preserves_records_and_foreign_keys(tmp_path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    database = tmp_path / "previous-head.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"

    previous = _run_alembic(backend_dir, database, "upgrade", "f4a6d9c123ab")
    assert previous.returncode == 0, previous.stdout + previous.stderr
    _seed_previous_head_records(database_url)

    upgrade = _run_alembic(backend_dir, database, "upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr

    engine = create_database_engine(database_url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {
            "alembic_version", "colleges", "users", "resources", "requests",
            "transfers", "transfer_status_history", "refresh_tokens",
        }
        assert {column["name"] for column in inspector.get_columns("requests")} == set(
            Base.metadata.tables["requests"].columns.keys()
        )
        assert len(inspector.get_foreign_keys("requests")) == 8
        assert {index["name"] for index in inspector.get_indexes("requests")} == {
            "ix_requests_resource_id_status",
            "ix_requests_requesting_college_id_status",
            "ix_requests_request_type_status",
        }
        with engine.connect() as connection:
            records = connection.execute(text(
                "SELECT id, request_type, offered_resource_id, offered_quantity, purpose "
                "FROM requests ORDER BY id"
            )).all()
            assert records == [
                (1, "exchange", 1, 3, "Existing valid exchange"),
                (2, "donation", None, None, "Existing donation request"),
            ]
            assert connection.execute(text(
                "SELECT (SELECT count(*) FROM colleges), (SELECT count(*) FROM users), "
                "(SELECT count(*) FROM resources), (SELECT count(*) FROM requests), "
                "(SELECT count(*) FROM transfers), (SELECT count(*) FROM transfer_status_history), "
                "(SELECT count(*) FROM refresh_tokens)"
            )).one() == (1, 1, 1, 2, 1, 1, 1)
            assert connection.execute(text(
                "SELECT request_id, resource_id, quantity, status FROM transfers WHERE id=1"
            )).one() == (1, 1, 1, "preparing")
            assert connection.execute(text(
                "SELECT transfer_id, actor_type, new_status FROM transfer_status_history WHERE id=1"
            )).one() == (1, "system", "preparing")
            assert connection.execute(text(
                "SELECT token_hash, jti FROM refresh_tokens WHERE id=1"
            )).one() == ("existing-token-hash", "existing-jti")
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "a73c5f91d2e4"
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []

            with pytest.raises(IntegrityError):
                connection.execute(text(
                    "INSERT INTO requests (resource_id, requesting_college_id, requested_by_user_id, "
                    "offered_resource_id, requested_quantity, offered_quantity, request_type, purpose, status) "
                    "VALUES (1, 1, 1, 1, 1, NULL, 'exchange', 'Missing offer quantity', 'pending')"
                ))
    finally:
        engine.dispose()

    downgrade = _run_alembic(backend_dir, database, "downgrade", "c81f23a7d940")
    assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
    engine = create_database_engine(database_url)
    try:
        with engine.connect() as connection:
            columns = {column["name"] for column in inspect(connection).get_columns("requests")}
            assert "approved_quantity" not in columns
            assert "rejection_reason" not in columns
            assert connection.execute(text("SELECT count(*) FROM requests")).scalar_one() == 2
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "c81f23a7d940"
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        engine.dispose()

    reupgrade = _run_alembic(backend_dir, database, "upgrade", "head")
    assert reupgrade.returncode == 0, reupgrade.stdout + reupgrade.stderr


def test_corrective_migration_runs_from_fresh_database(tmp_path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    database = tmp_path / "fresh.sqlite3"
    upgrade = _run_alembic(backend_dir, database, "upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr

    engine = create_database_engine(f"sqlite:///{database.as_posix()}")
    try:
        assert set(inspect(engine).get_table_names()) == {
            "alembic_version", "colleges", "users", "resources", "requests",
            "transfers", "transfer_status_history", "refresh_tokens",
        }
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "a73c5f91d2e4"
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.execute(text("PRAGMA foreign_key_check")).all() == []
    finally:
        engine.dispose()


def test_phase_seven_migration_from_current_head_preserves_populated_database(tmp_path) -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    database = tmp_path / "phase-seven-current-head.sqlite3"
    database_url = f"sqlite:///{database.as_posix()}"
    previous = _run_alembic(backend_dir, database, "upgrade", "c81f23a7d940")
    assert previous.returncode == 0, previous.stdout + previous.stderr
    _seed_previous_head_records(database_url)

    upgrade = _run_alembic(backend_dir, database, "upgrade", "head")
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
    engine = create_database_engine(database_url)
    try:
        inspector = inspect(engine)
        assert set(inspector.get_table_names()) == {
            "alembic_version", "colleges", "users", "resources", "requests",
            "transfers", "transfer_status_history", "refresh_tokens",
        }
        assert {column["name"] for column in inspector.get_columns("requests")} == set(
            Base.metadata.tables["requests"].columns.keys()
        )
        with engine.connect() as connection:
            assert connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "a73c5f91d2e4"
            assert connection.execute(text("SELECT count(*) FROM requests")).scalar_one() == 2
            assert connection.execute(text("SELECT count(*) FROM transfers")).scalar_one() == 1
            assert connection.execute(text("SELECT rejection_reason, approved_quantity, cancellation_requested_at FROM requests WHERE id=1")).one() == (None, None, None)
            assert connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one() == 1
            assert connection.exec_driver_sql("PRAGMA foreign_key_check").all() == []
    finally:
        engine.dispose()
