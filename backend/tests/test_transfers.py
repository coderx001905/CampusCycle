from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.db.session import create_database_engine, get_db
from app.main import create_app
from app.models import Base, College, Request, Resource, Transfer, TransferStatusHistory, User


@pytest.fixture
def transfer_context(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'phase8.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        jwt_secret_key="phase-eight-test-jwt-secret-key-with-32-bytes",
        csrf_secret_key="phase-eight-test-csrf-secret-key-with-32-bytes",
        cors_origins=["http://localhost:5173"],
    )
    with sessions.begin() as db:
        colleges = {
            key: College(
                name=f"{key} College",
                address="1 Campus Road",
                city="Test City",
                contact_email=f"{key}@example.edu",
                verification_status=status,
            )
            for key, status in (
                ("owner", "verified"),
                ("buyer", "verified"),
                ("other", "verified"),
                ("pending", "pending"),
                ("rejected", "rejected"),
            )
        }
        db.add_all(colleges.values())
        db.flush()
        users = {
            key: User(
                name=f"{key} rep",
                email=f"{key}-rep@example.edu",
                password_hash="test-hash",
                role="college_representative",
                college_id=college.id,
                is_active=True,
            )
            for key, college in colleges.items()
        }
        users["admin"] = User(
            name="Admin",
            email="admin@example.edu",
            password_hash="test-hash",
            role="platform_admin",
            college_id=None,
            is_active=True,
        )
        db.add_all(users.values())
        db.flush()
        ids = {key: user.id for key, user in users.items()}
        college_ids = {key: college.id for key, college in colleges.items()}

    def override_db():
        db = sessions()
        try:
            yield db
        finally:
            db.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    client.__enter__()
    tokens = {
        key: create_access_token(
            subject=str(user_id),
            role=users[key].role,
            college_id=users[key].college_id,
            settings=settings,
        )
        for key, user_id in ids.items()
    }
    context = {
        "app": app,
        "client": client,
        "sessions": sessions,
        "engine": engine,
        "ids": ids,
        "college_ids": college_ids,
        "tokens": tokens,
    }
    try:
        yield context
    finally:
        client.__exit__(None, None, None)
        app.dependency_overrides.clear()
        engine.dispose()


def auth(ctx, key):
    return {"Authorization": f"Bearer {ctx['tokens'][key]}"}


def add_resource(ctx, *, owner="owner", kind="donation", quantity=20, status="active"):
    with ctx["sessions"].begin() as db:
        user = db.get(User, ctx["ids"][owner])
        resource = Resource(
            college_id=user.college_id,
            created_by_user_id=user.id,
            name=f"{kind} resource",
            category="Lab Equipment",
            condition="Good",
            quantity_total=quantity,
            quantity_available=quantity,
            quantity_reserved=0,
            unit="units",
            transfer_type=kind,
            status=status,
        )
        db.add(resource)
        db.flush()
        return resource.id


def create_approved_request(
    ctx, *, kind="donation", requested=10, approved=10, offered_qty=None
):
    resource_type = {"purchase_enquiry": "sale"}.get(kind, kind)
    res_id = add_resource(ctx, owner="owner", kind=resource_type, quantity=20)
    payload = {
        "resource_id": res_id,
        "request_type": kind,
        "requested_quantity": requested,
        "purpose": "Logistics test transfer purpose",
    }
    if kind == "exchange":
        offered_res_id = add_resource(
            ctx, owner="buyer", kind="exchange", quantity=20
        )
        payload["offered_resource_id"] = offered_res_id
        payload["offered_quantity"] = offered_qty or 5

    res = ctx["client"].post("/api/v1/requests", headers=auth(ctx, "buyer"), json=payload)
    assert res.status_code == 201, res.text
    req_id = res.json()["data"]["id"]

    # Owner approves request
    app_payload = {"approved_quantity": approved} if kind == "donation" else None
    res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/approve",
        headers=auth(ctx, "owner"),
        json=app_payload,
    )
    assert res.status_code == 200, res.text

    if kind == "purchase_enquiry":
        # Buyer confirms purchase intent
        res = ctx["client"].post(
            f"/api/v1/requests/{req_id}/confirm-purchase",
            headers=auth(ctx, "buyer"),
        )
        assert res.status_code == 200, res.text

    return req_id, res_id


# ---------------------------------------------------------------------------
# Test 1: Partial batch creation
# ---------------------------------------------------------------------------
def test_partial_batch_creation(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4, "dispatch_notes": "First batch of 4"},
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["quantity"] == 4
    assert data["status"] == "preparing"
    assert data["request_id"] == req_id
    assert data["resource_id"] == res_id

    # Verify request status transitioned to in_progress
    with ctx["sessions"]() as db:
        req = db.get(Request, req_id)
        assert req.status == "in_progress"


# ---------------------------------------------------------------------------
# Test 2: Multiple batches within approved quantity
# ---------------------------------------------------------------------------
def test_multiple_batches_within_approved_quantity(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    res1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    assert res1.status_code == 201

    res2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 6},
    )
    assert res2.status_code == 201


# ---------------------------------------------------------------------------
# Test 3: Aggregate quantity exceeding approval
# ---------------------------------------------------------------------------
def test_aggregate_quantity_exceeding_approval(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    res1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 6},
    )
    assert res1.status_code == 201

    res2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 5},
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "quantity_exceeds_approved"


# ---------------------------------------------------------------------------
# Test 4: Invalid transfer leg
# ---------------------------------------------------------------------------
def test_invalid_transfer_leg(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "offered_resource", "quantity": 4},
    )
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "invalid_transfer_leg"


# ---------------------------------------------------------------------------
# Test 5: Cross-college authorization failures
# ---------------------------------------------------------------------------
def test_cross_college_authorization_failures(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    # Buyer cannot create transfer for requested_resource
    res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "buyer"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    assert res.status_code == 403

    # Other college cannot create transfer
    res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "other"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    assert res.status_code == 403

    # Pending college cannot create transfer
    res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "pending"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    assert res.status_code == 403

    # Unrelated college cannot view transfer
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    t_id = t_res.json()["data"]["id"]

    get_res = ctx["client"].get(f"/api/v1/transfers/{t_id}", headers=auth(ctx, "other"))
    assert get_res.status_code == 404


# ---------------------------------------------------------------------------
# Test 6: Unauthorized dispatch
# ---------------------------------------------------------------------------
def test_unauthorized_dispatch(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    t_id = t_res.json()["data"]["id"]

    # Buyer cannot dispatch
    res = ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "buyer"))
    assert res.status_code == 403

    # Other college cannot dispatch
    res = ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "other"))
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Test 7: Duplicate dispatch
# ---------------------------------------------------------------------------
def test_duplicate_dispatch(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    t_id = t_res.json()["data"]["id"]

    res1 = ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "owner"))
    assert res1.status_code == 200
    assert res1.json()["data"]["status"] == "dispatched"

    # Second dispatch attempt fails
    res2 = ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "owner"))
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "invalid_transfer_state"


# ---------------------------------------------------------------------------
# Test 8: Successful receipt
# ---------------------------------------------------------------------------
def test_successful_receipt(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    )
    t_id = t_res.json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "owner"))

    res = ctx["client"].post(
        f"/api/v1/transfers/{t_id}/receipt",
        headers=auth(ctx, "buyer"),
        json={
            "quantity_received_good": 10,
            "quantity_damaged": 0,
            "quantity_missing": 0,
            "receipt_confirmation": "All 10 received in good shape.",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "completed"
    assert data["completed_at"] is not None
    assert data["dispute_status"] == "none"

    # Check inventory accounting
    with ctx["sessions"]() as db:
        resource = db.get(Resource, res_id)
        assert resource.quantity_total == 10  # 20 - 10
        assert resource.quantity_reserved == 0
        assert resource.quantity_available == 10
        assert resource.quantity_available + resource.quantity_reserved == resource.quantity_total


# ---------------------------------------------------------------------------
# Test 9: Damaged receipt
# ---------------------------------------------------------------------------
def test_damaged_receipt(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    )
    t_id = t_res.json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "owner"))

    res = ctx["client"].post(
        f"/api/v1/transfers/{t_id}/receipt",
        headers=auth(ctx, "buyer"),
        json={
            "quantity_received_good": 7,
            "quantity_damaged": 3,
            "quantity_missing": 0,
            "receipt_confirmation": "7 good, 3 damaged.",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "disputed"
    assert data["dispute_status"] == "open"

    with ctx["sessions"]() as db:
        resource = db.get(Resource, res_id)
        # Good items deducted (7), damaged items (3) remain reserved
        assert resource.quantity_total == 13  # 20 - 7
        assert resource.quantity_reserved == 3
        assert resource.quantity_available == 10
        assert resource.quantity_available + resource.quantity_reserved == resource.quantity_total


# ---------------------------------------------------------------------------
# Test 10: Missing receipt
# ---------------------------------------------------------------------------
def test_missing_receipt(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    )
    t_id = t_res.json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "owner"))

    res = ctx["client"].post(
        f"/api/v1/transfers/{t_id}/receipt",
        headers=auth(ctx, "buyer"),
        json={
            "quantity_received_good": 8,
            "quantity_damaged": 0,
            "quantity_missing": 2,
            "receipt_confirmation": "8 good, 2 missing.",
        },
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["status"] == "disputed"
    assert data["dispute_status"] == "open"

    with ctx["sessions"]() as db:
        resource = db.get(Resource, res_id)
        assert resource.quantity_total == 12  # 20 - 8
        assert resource.quantity_reserved == 2
        assert resource.quantity_available == 10
        assert resource.quantity_available + resource.quantity_reserved == resource.quantity_total


# ---------------------------------------------------------------------------
# Test 11: Invalid receipt quantity totals
# ---------------------------------------------------------------------------
def test_invalid_receipt_quantity_totals(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    )
    t_id = t_res.json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "owner"))

    # Sum is 8 != 10
    res1 = ctx["client"].post(
        f"/api/v1/transfers/{t_id}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 6, "quantity_damaged": 2, "quantity_missing": 0},
    )
    assert res1.status_code == 422
    assert res1.json()["error"]["code"] == "invalid_receipt_quantities"

    # Sum is 12 != 10
    res2 = ctx["client"].post(
        f"/api/v1/transfers/{t_id}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 2},
    )
    assert res2.status_code == 422
    assert res2.json()["error"]["code"] == "invalid_receipt_quantities"


# ---------------------------------------------------------------------------
# Test 12: Transfer history creation
# ---------------------------------------------------------------------------
def test_transfer_history_creation(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10, "dispatch_notes": "Init batch"},
    )
    t_id = t_res.json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t_id}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t_id}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 10, "quantity_damaged": 0, "quantity_missing": 0},
    )

    h_res = ctx["client"].get(f"/api/v1/transfers/{t_id}/history", headers=auth(ctx, "buyer"))
    assert h_res.status_code == 200
    items = h_res.json()["data"]["items"]
    assert len(items) == 3
    assert items[0]["previous_status"] is None and items[0]["new_status"] == "preparing"
    assert items[1]["previous_status"] == "preparing" and items[1]["new_status"] == "dispatched"
    assert items[2]["previous_status"] == "dispatched" and items[2]["new_status"] == "completed"


# ---------------------------------------------------------------------------
# Test 13: Pre-dispatch cancellation
# ---------------------------------------------------------------------------
def test_pre_dispatch_cancellation(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    )
    t_id = t_res.json()["data"]["id"]

    # Buyer requests cancellation
    c_res = ctx["client"].post(
        f"/api/v1/transfers/{t_id}/cancel",
        headers=auth(ctx, "buyer"),
        json={"reason": "Need to cancel batch"},
    )
    assert c_res.status_code == 200
    assert c_res.json()["data"]["status"] == "cancellation_pending"

    # Before dispatch, resource-owning college representative reviews
    d_res = ctx["client"].post(
        f"/api/v1/transfers/{t_id}/cancellation-decision",
        headers=auth(ctx, "owner"),
        json={"decision": "approved"},
    )
    assert d_res.status_code == 200
    assert d_res.json()["data"]["status"] == "cancelled"

    # Check that reserved quantity was released
    with ctx["sessions"]() as db:
        resource = db.get(Resource, res_id)
        # Initial res was 10. 4 was released. Res should be 6, avail 14.
        assert resource.quantity_reserved == 6
        assert resource.quantity_available == 14
        assert resource.quantity_available + resource.quantity_reserved == resource.quantity_total


# ---------------------------------------------------------------------------
# Test 14: Post-dispatch cancellation
# ---------------------------------------------------------------------------
def test_post_dispatch_cancellation(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    # Batch 1 of 5 dispatched
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 5},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))

    # Batch 2 of 5 preparing
    t2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 5},
    ).json()["data"]["id"]

    # Buyer requests cancellation of Batch 2
    ctx["client"].post(
        f"/api/v1/transfers/{t2}/cancel",
        headers=auth(ctx, "buyer"),
        json={"reason": "Cancel unshipped batch 2"},
    )

    # Since a batch was dispatched, owner rep review MUST fail (Platform Admin required)
    owner_dec = ctx["client"].post(
        f"/api/v1/transfers/{t2}/cancellation-decision",
        headers=auth(ctx, "owner"),
        json={"decision": "approved"},
    )
    assert owner_dec.status_code == 403

    # Platform Admin approves cancellation of unshipped Batch 2
    admin_dec = ctx["client"].post(
        f"/api/v1/transfers/{t2}/cancellation-decision",
        headers=auth(ctx, "admin"),
        json={"decision": "approved"},
    )
    assert admin_dec.status_code == 200
    assert admin_dec.json()["data"]["status"] == "cancelled"

    # Attempting to cancel Batch 1 (which was dispatched) is blocked
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/cancel",
        headers=auth(ctx, "buyer"),
        json={"reason": "Cancel dispatched batch 1"},
    )
    admin_dec1 = ctx["client"].post(
        f"/api/v1/transfers/{t1}/cancellation-decision",
        headers=auth(ctx, "admin"),
        json={"decision": "approved"},
    )
    assert admin_dec1.status_code == 409
    assert admin_dec1.json()["error"]["code"] == "cannot_cancel_dispatched"


# ---------------------------------------------------------------------------
# Test 15: Cancellation rejection
# ---------------------------------------------------------------------------
def test_cancellation_rejection(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 5},
    ).json()["data"]["id"]

    ctx["client"].post(
        f"/api/v1/transfers/{t}/cancel",
        headers=auth(ctx, "buyer"),
        json={"reason": "Cancel please"},
    )
    dec = ctx["client"].post(
        f"/api/v1/transfers/{t}/cancellation-decision",
        headers=auth(ctx, "owner"),
        json={"decision": "rejected"},
    )
    assert dec.status_code == 200
    assert dec.json()["data"]["status"] == "preparing"


# ---------------------------------------------------------------------------
# Test 16: Dispute resolution by Platform Admin
# ---------------------------------------------------------------------------
def test_dispute_resolution_by_platform_admin(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )

    res = ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "Damage verified and accepted."},
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["dispute_status"] == "resolved"
    assert data["dispute_outcome"] == "accept_report"
    assert data["status"] == "completed"


# ---------------------------------------------------------------------------
# Test 17: Dispute resolution denied to College Representative
# ---------------------------------------------------------------------------
def test_dispute_resolution_denied_to_college_representative(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )

    res_owner = ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "owner"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "I accept"},
    )
    assert res_owner.status_code == 403

    res_buyer = ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "buyer"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "I accept"},
    )
    assert res_buyer.status_code == 403


# ---------------------------------------------------------------------------
# Test 18: Accept-report inventory accounting
# ---------------------------------------------------------------------------
def test_accept_report_inventory_accounting(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 7, "quantity_damaged": 2, "quantity_missing": 1},
    )

    # Initial res=10, avail=10, tot=20.
    # At receipt: good=7 deducted -> tot=13, res=3, avail=10.
    ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "Accepted report."},
    )

    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        # Damaged and missing quantities (3) remain reserved; NOT automatically written off
        assert res.quantity_total == 13
        assert res.quantity_reserved == 3
        assert res.quantity_available == 10
        assert res.quantity_available + res.quantity_reserved == res.quantity_total

        # Parent request cannot complete while disputed inventory remains unaccounted for
        req = db.get(Request, req_id)
        assert req.status == "in_progress"


# ---------------------------------------------------------------------------
# Test 19: Replacement approval and reservation
# ---------------------------------------------------------------------------
def test_replacement_approval_and_reservation(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )

    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Send replacement of 2"},
    )

    # Owner creates replacement transfer
    repl_res = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 2, "replacement_for_transfer_id": t1},
    )
    assert repl_res.status_code == 201

    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        # Prior to repl: tot=12, res=2, avail=10.
        # Repl reserved 2: avail becomes 8, res becomes 4, tot=12.
        assert res.quantity_available == 8
        assert res.quantity_reserved == 4
        assert res.quantity_total == 12
        assert res.quantity_available + res.quantity_reserved == res.quantity_total


# ---------------------------------------------------------------------------
# Test 20: Original disputed inventory held until replacement receipt
# ---------------------------------------------------------------------------
def test_original_disputed_inventory_held_until_replacement_receipt(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Replace 2"},
    )
    t2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 2, "replacement_for_transfer_id": t1},
    ).json()["data"]["id"]

    # Dispatch replacement batch
    ctx["client"].post(f"/api/v1/transfers/{t2}/dispatch", headers=auth(ctx, "owner"))

    # Prior to receipt of replacement, original disputed inventory (2) is still held in reserved
    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        assert res.quantity_reserved == 4  # 2 original disputed + 2 replacement in-flight
        assert res.quantity_available == 8


# ---------------------------------------------------------------------------
# Test 21: Original disputed inventory written off exactly once after replacement receipt
# ---------------------------------------------------------------------------
def test_original_disputed_inventory_written_off_exactly_once_after_replacement_receipt(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Replace 2"},
    )
    t2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 2, "replacement_for_transfer_id": t1},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t2}/dispatch", headers=auth(ctx, "owner"))

    # Buyer receives replacement
    rec_res = ctx["client"].post(
        f"/api/v1/transfers/{t2}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 2, "quantity_damaged": 0, "quantity_missing": 0},
    )
    assert rec_res.status_code == 200

    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        # Delivered 2 replacement units (deducted: tot 12->10, res 4->2)
        # Original 2 disputed units written off (deducted: tot 10->8, res 2->0)
        assert res.quantity_total == 8
        assert res.quantity_reserved == 0
        assert res.quantity_available == 8
        assert res.quantity_available + res.quantity_reserved == res.quantity_total

        # Request should now be completed!
        req = db.get(Request, req_id)
        assert req.status == "completed"


# ---------------------------------------------------------------------------
# Test 22: Claim rejection retaining reserved stock
# ---------------------------------------------------------------------------
def test_claim_rejection_retaining_reserved_stock(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 9, "quantity_damaged": 0, "quantity_missing": 1},
    )

    ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "claim_rejected", "dispute_resolution": "Claim could not be verified."},
    )

    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        # 9 delivered (tot 20->11, res 10->1)
        # 1 claimed missing is retained in reserved
        assert res.quantity_total == 11
        assert res.quantity_reserved == 1
        assert res.quantity_available == 10
        assert res.quantity_available + res.quantity_reserved == res.quantity_total

        # Parent request cannot complete while disputed inventory remains
        req = db.get(Request, req_id)
        assert req.status == "in_progress"


# ---------------------------------------------------------------------------
# Test 23: Duplicate dispute resolution
# ---------------------------------------------------------------------------
def test_duplicate_dispute_resolution(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )

    res1 = ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "Accepted"},
    )
    assert res1.status_code == 200

    # Second attempt fails with 409
    res2 = ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "Accepted again"},
    )
    assert res2.status_code == 409
    assert res2.json()["error"]["code"] == "invalid_dispute_state"


# ---------------------------------------------------------------------------
# Test 24: Request completion across multiple batches
# ---------------------------------------------------------------------------
def test_request_completion_across_multiple_batches(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    # Batch 1 of 6
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 6},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 6, "quantity_damaged": 0, "quantity_missing": 0},
    )

    # After batch 1, request must not be completed
    with ctx["sessions"]() as db:
        assert db.get(Request, req_id).status == "in_progress"

    # Batch 2 of 4
    t2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t2}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t2}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 4, "quantity_damaged": 0, "quantity_missing": 0},
    )

    # After batch 2, full quantity (10) received, request moves to completed
    with ctx["sessions"]() as db:
        req = db.get(Request, req_id)
        assert req.status == "completed"
        assert req.updated_at is not None


# ---------------------------------------------------------------------------
# Test 25: Exchange completion across both movement legs
# ---------------------------------------------------------------------------
def test_exchange_completion_across_both_movement_legs(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(
        ctx, kind="exchange", requested=8, approved=8, offered_qty=4
    )

    # Leg 1: requested_resource (source: owner, dest: buyer, qty: 8)
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 8},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 0, "quantity_missing": 0},
    )

    # Leg 1 complete, but Leg 2 has not started; request must remain in_progress
    with ctx["sessions"]() as db:
        assert db.get(Request, req_id).status == "in_progress"

    # Leg 2: offered_resource (source: buyer, dest: owner, qty: 4)
    t2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "buyer"),
        json={"transfer_leg": "offered_resource", "quantity": 4},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t2}/dispatch", headers=auth(ctx, "buyer"))
    ctx["client"].post(
        f"/api/v1/transfers/{t2}/receipt",
        headers=auth(ctx, "owner"),
        json={"quantity_received_good": 4, "quantity_damaged": 0, "quantity_missing": 0},
    )

    # Both legs complete; request moves to completed
    with ctx["sessions"]() as db:
        req = db.get(Request, req_id)
        assert req.status == "completed"


# ---------------------------------------------------------------------------
# Test 26: Inventory balance invariants
# ---------------------------------------------------------------------------
def test_inventory_balance_invariants(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    def assert_inv(step_name):
        with ctx["sessions"]() as db:
            r = db.get(Resource, res_id)
            assert (
                r.quantity_available + r.quantity_reserved == r.quantity_total
            ), f"Invariant broken at step {step_name}: avail={r.quantity_available}, res={r.quantity_reserved}, tot={r.quantity_total}"

    assert_inv("after request approval")

    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 5},
    ).json()["data"]["id"]
    assert_inv("after transfer create")

    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    assert_inv("after dispatch")

    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 3, "quantity_damaged": 1, "quantity_missing": 1},
    )
    assert_inv("after disputed receipt")

    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "Accepted"},
    )
    assert_inv("after dispute resolution accept_report")


# ---------------------------------------------------------------------------
# Test 27: Concurrent reservation and inventory integrity
# ---------------------------------------------------------------------------
def test_concurrent_reservation_and_inventory_integrity(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    # Attempt to create two transfers of 6 concurrently when only 10 is approved
    def create_batch(qty):
        return ctx["client"].post(
            f"/api/v1/requests/{req_id}/transfers",
            headers=auth(ctx, "owner"),
            json={"transfer_leg": "requested_resource", "quantity": qty},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(create_batch, 6)
        f2 = executor.submit(create_batch, 6)
        r1 = f1.result()
        r2 = f2.result()

    statuses = [r1.status_code, r2.status_code]
    assert 201 in statuses
    assert 409 in statuses

    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        assert res.quantity_available + res.quantity_reserved == res.quantity_total


# ---------------------------------------------------------------------------
# Test 28: Replacement transfer cannot exceed available replacement stock
# ---------------------------------------------------------------------------
def test_replacement_transfer_cannot_exceed_available_replacement_stock(transfer_context):
    ctx = transfer_context
    # Create resource with exactly 10 units total
    res_id = add_resource(ctx, owner="owner", kind="donation", quantity=10)
    p = ctx["client"].post(
        "/api/v1/requests",
        headers=auth(ctx, "buyer"),
        json={
            "resource_id": res_id,
            "request_type": "donation",
            "requested_quantity": 10,
            "purpose": "All 10",
        },
    )
    req_id = p.json()["data"]["id"]
    ctx["client"].post(
        f"/api/v1/requests/{req_id}/approve",
        headers=auth(ctx, "owner"),
        json={"approved_quantity": 10},
    )

    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Replace 2"},
    )

    # Resource available stock is 0 (tot=8, res=2, avail=0).
    # Attempting to create replacement transfer for 2 units must fail with 409 insufficient_stock
    repl = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 2, "replacement_for_transfer_id": t1},
    )
    assert repl.status_code == 409
    assert repl.json()["error"]["code"] == "insufficient_stock"


# ---------------------------------------------------------------------------
# Additional coverage: list transfers, query filters, and get transfer
# ---------------------------------------------------------------------------
def test_transfers_list_and_detail(transfer_context):
    ctx = transfer_context
    req_id, _ = create_approved_request(ctx, kind="donation", requested=10, approved=10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 5},
    ).json()["data"]["id"]

    # Owner lists transfers
    l_owner = ctx["client"].get("/api/v1/transfers", headers=auth(ctx, "owner"))
    assert l_owner.status_code == 200
    assert len(l_owner.json()["data"]["items"]) >= 1

    # Buyer lists transfers
    l_buyer = ctx["client"].get("/api/v1/transfers", headers=auth(ctx, "buyer"))
    assert l_buyer.status_code == 200
    assert len(l_buyer.json()["data"]["items"]) >= 1

    # Other college lists transfers (should see 0)
    l_other = ctx["client"].get("/api/v1/transfers", headers=auth(ctx, "other"))
    assert l_other.status_code == 200
    assert len(l_other.json()["data"]["items"]) == 0

    # Admin lists transfers
    l_admin = ctx["client"].get("/api/v1/transfers", headers=auth(ctx, "admin"))
    assert l_admin.status_code == 200
    assert len(l_admin.json()["data"]["items"]) >= 1

    # Detail view
    d_res = ctx["client"].get(f"/api/v1/transfers/{t}", headers=auth(ctx, "owner"))
    assert d_res.status_code == 200
    assert d_res.json()["data"]["id"] == t


# ---------------------------------------------------------------------------
# Test 30: Request completion blocked while disputed inventory remains
# ---------------------------------------------------------------------------
def test_parent_request_completion_blocked_by_unaccounted_disputes(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    # Dispatch full approved quantity (10)
    t = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t}/dispatch", headers=auth(ctx, "owner"))

    # Receipt with damage: 8 good, 2 damaged
    ctx["client"].post(
        f"/api/v1/transfers/{t}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )

    # Admin resolves with accept_report
    ctx["client"].post(
        f"/api/v1/transfers/{t}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "accept_report", "dispute_resolution": "Accepted report."},
    )

    # Even though dispute is resolved, 2 items remain damaged and reserved in inventory.
    # The parent request MUST NOT be marked completed.
    with ctx["sessions"]() as db:
        req = db.get(Request, req_id)
        assert req.status == "in_progress"
        r = db.get(Resource, res_id)
        assert r.quantity_reserved == 2
        assert r.quantity_total == 12
        assert r.quantity_available == 10


# ---------------------------------------------------------------------------
# Test 31: Multiple replacement batches linked to one original disputed transfer
# ---------------------------------------------------------------------------
def test_multiple_replacement_batches_and_aggregate_completion(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    # Dispatch original batch of 10
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))

    # Receipt with 6 good and 4 damaged
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 6, "quantity_damaged": 4, "quantity_missing": 0},
    )

    # Admin approves replacement
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Replace 4 damaged units in two partial batches."},
    )

    # 1. Create first partial replacement batch of 2
    r1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 2, "replacement_for_transfer_id": t1},
    )
    assert r1.status_code == 201
    t2 = r1.json()["data"]["id"]

    # 2. Create second partial replacement batch of 2
    r2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 2, "replacement_for_transfer_id": t1},
    )
    assert r2.status_code == 201
    t3 = r2.json()["data"]["id"]

    # 3. Exceeding the original disputed quantity (2 + 2 + 1 > 4) MUST fail
    r3 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 1, "replacement_for_transfer_id": t1},
    )
    assert r3.status_code == 409
    assert r3.json()["error"]["code"] == "quantity_exceeds_disputed"

    # Inventory before dispatch: 4 original disputed reserved + 4 replacement reserved = 8 reserved, 6 available, 14 total
    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        assert res.quantity_reserved == 8
        assert res.quantity_available == 6
        assert res.quantity_total == 14
        assert res.quantity_available + res.quantity_reserved == res.quantity_total

    # Dispatch and receive first replacement batch
    ctx["client"].post(f"/api/v1/transfers/{t2}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t2}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 2, "quantity_damaged": 0, "quantity_missing": 0},
    )

    # After first batch: 2 replacement delivered and 2 original disputed written off
    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        # Delivered 2 repl -> tot 14->12, res 8->6. Written off 2 orig -> tot 12->10, res 6->4.
        assert res.quantity_total == 10
        assert res.quantity_reserved == 4  # 2 orig disputed + 2 repl batch 2
        assert res.quantity_available == 6
        assert res.quantity_available + res.quantity_reserved == res.quantity_total

        # Request is NOT complete yet (only 6 orig + 2 repl = 8 good; needed 4, only 2 delivered)
        req = db.get(Request, req_id)
        assert req.status == "in_progress"

    # Dispatch and receive second replacement batch
    ctx["client"].post(f"/api/v1/transfers/{t3}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t3}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 2, "quantity_damaged": 0, "quantity_missing": 0},
    )

    # After second batch: remaining 2 repl delivered and remaining 2 orig disputed written off
    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        assert res.quantity_total == 6
        assert res.quantity_reserved == 0
        assert res.quantity_available == 6
        assert res.quantity_available + res.quantity_reserved == res.quantity_total

        # Now all 10 approved items have been verified received in good condition, and 0 disputed items remain.
        req = db.get(Request, req_id)
        assert req.status == "completed"


# ---------------------------------------------------------------------------
# Test 32: Partial and damaged replacement receipt accounting
# ---------------------------------------------------------------------------
def test_partial_and_damaged_replacement_receipt_accounting(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    # Original transfer of 10
    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 6, "quantity_damaged": 4, "quantity_missing": 0},
    )
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Replace 4."},
    )

    # Replacement batch of 4
    t2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 4, "replacement_for_transfer_id": t1},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t2}/dispatch", headers=auth(ctx, "owner"))

    # Replacement receipt has good, damaged, and missing items: 2 good, 1 damaged, 1 missing
    rec = ctx["client"].post(
        f"/api/v1/transfers/{t2}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 2, "quantity_damaged": 1, "quantity_missing": 1},
    )
    assert rec.status_code == 200
    data = rec.json()["data"]
    assert data["status"] == "disputed"
    assert data["dispute_status"] == "open"

    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        # Prior to receipt: tot=14, res=8 (4 orig + 4 repl), avail=6.
        # 2 repl good delivered: tot -= 2, res -= 2 (now tot=12, res=6).
        # Exactly 2 orig disputed written off (proportional to 2 good replacement units): tot -= 2, res -= 2 (now tot=10, res=4).
        # In reserved: 2 orig disputed remaining + 1 damaged repl + 1 missing repl = 4 reserved.
        assert res.quantity_total == 10
        assert res.quantity_reserved == 4
        assert res.quantity_available == 6
        assert res.quantity_available + res.quantity_reserved == res.quantity_total

        # Parent request MUST remain in_progress
        req = db.get(Request, req_id)
        assert req.status == "in_progress"


# ---------------------------------------------------------------------------
# Test 33: Duplicate receipt and dispute calls cannot cause double adjustments
# ---------------------------------------------------------------------------
def test_duplicate_receipt_and_dispute_cannot_double_adjust(transfer_context):
    ctx = transfer_context
    req_id, res_id = create_approved_request(ctx, kind="donation", requested=10, approved=10)

    t1 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 10},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t1}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 8, "quantity_damaged": 2, "quantity_missing": 0},
    )
    ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Replace 2."},
    )

    t2 = ctx["client"].post(
        f"/api/v1/requests/{req_id}/transfers",
        headers=auth(ctx, "owner"),
        json={"transfer_leg": "requested_resource", "quantity": 2, "replacement_for_transfer_id": t1},
    ).json()["data"]["id"]
    ctx["client"].post(f"/api/v1/transfers/{t2}/dispatch", headers=auth(ctx, "owner"))
    ctx["client"].post(
        f"/api/v1/transfers/{t2}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 2, "quantity_damaged": 0, "quantity_missing": 0},
    )

    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        assert res.quantity_total == 8
        assert res.quantity_reserved == 0
        assert res.quantity_available == 8

    # Attempting duplicate receipt on completed replacement batch t2 MUST fail with 409
    dup_receipt = ctx["client"].post(
        f"/api/v1/transfers/{t2}/receipt",
        headers=auth(ctx, "buyer"),
        json={"quantity_received_good": 2, "quantity_damaged": 0, "quantity_missing": 0},
    )
    assert dup_receipt.status_code == 409
    assert dup_receipt.json()["error"]["code"] == "invalid_transfer_state"

    # Attempting duplicate dispute resolution on t1 MUST fail with 409
    dup_dispute = ctx["client"].post(
        f"/api/v1/transfers/{t1}/dispute-resolution",
        headers=auth(ctx, "admin"),
        json={"dispute_outcome": "replacement_approved", "dispute_resolution": "Replace again."},
    )
    assert dup_dispute.status_code == 409
    assert dup_dispute.json()["error"]["code"] == "invalid_dispute_state"

    # Inventory must remain exactly the same (no double deduction)
    with ctx["sessions"]() as db:
        res = db.get(Resource, res_id)
        assert res.quantity_total == 8
        assert res.quantity_reserved == 0
        assert res.quantity_available == 8
        assert res.quantity_available + res.quantity_reserved == res.quantity_total


