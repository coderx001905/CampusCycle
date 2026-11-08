from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.errors import APIError
from app.core.security import create_access_token
from app.db.session import create_database_engine, get_db
from app.main import create_app
from app.models import Base, College, Request, Resource, Transfer, User
from app.services.requests import approve_request


@pytest.fixture
def request_context(tmp_path: Path):
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'phase7.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(_env_file=None,
                        jwt_secret_key="phase-seven-test-jwt-secret-key-with-32-bytes",
                        csrf_secret_key="phase-seven-test-csrf-secret-key-with-32-bytes",
                        cors_origins=["http://localhost:5173"])
    with sessions.begin() as db:
        colleges = {
            key: College(name=f"{key} College", address="1 Campus Road", city="Test City",
                         contact_email=f"{key}@example.edu", verification_status=status)
            for key, status in (("owner", "verified"), ("buyer", "verified"),
                                ("other", "verified"), ("pending", "pending"),
                                ("rejected", "rejected"))
        }
        db.add_all(colleges.values())
        db.flush()
        users = {
            key: User(name=f"{key} rep", email=f"{key}-rep@example.edu", password_hash="test-hash",
                      role="college_representative", college_id=college.id, is_active=True)
            for key, college in colleges.items()
        }
        users["admin"] = User(name="Admin", email="admin@example.edu", password_hash="test-hash",
                              role="platform_admin", college_id=None, is_active=True)
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
    tokens = {key: create_access_token(subject=str(user_id), role=users[key].role,
                                       college_id=users[key].college_id, settings=settings)
              for key, user_id in ids.items()}
    context = {"app": app, "client": client, "sessions": sessions, "engine": engine,
               "ids": ids, "college_ids": college_ids, "tokens": tokens}
    try:
        yield context
    finally:
        client.__exit__(None, None, None)
        app.dependency_overrides.clear()
        engine.dispose()


def auth(ctx, key):
    return {"Authorization": f"Bearer {ctx['tokens'][key]}"}


def add_resource(ctx, *, owner="owner", kind="donation", quantity=10, status="active"):
    with ctx["sessions"].begin() as db:
        user = db.get(User, ctx["ids"][owner])
        resource = Resource(college_id=user.college_id, created_by_user_id=user.id,
                            name=f"{kind} resource", category="Books", condition="Used",
                            quantity_total=quantity, quantity_available=quantity, quantity_reserved=0,
                            unit="pieces", transfer_type=kind, status=status)
        db.add(resource)
        db.flush()
        return resource.id


def make_request(ctx, *, kind="donation", resource_id=None, requested=4,
                 offered_id=None, offered=2):
    resource_id = resource_id or add_resource(ctx, kind={"purchase_enquiry": "sale"}.get(kind, kind))
    payload = {"resource_id": resource_id, "request_type": kind,
               "requested_quantity": requested, "purpose": "For the campus library"}
    if kind == "exchange":
        payload.update(offered_resource_id=offered_id or add_resource(ctx, owner="buyer", kind="exchange"),
                       offered_quantity=offered)
    response = ctx["client"].post("/api/v1/requests", headers=auth(ctx, "buyer"), json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]["id"]


def quantities(ctx, resource_id):
    with ctx["sessions"]() as db:
        resource = db.get(Resource, resource_id)
        return resource.quantity_total, resource.quantity_available, resource.quantity_reserved


def test_create_donation_exchange_and_purchase_and_mine_received_scoping(request_context):
    ctx = request_context
    donation = add_resource(ctx)
    exchange = add_resource(ctx, kind="exchange")
    sale = add_resource(ctx, kind="sale")
    ids = [make_request(ctx, resource_id=donation), make_request(ctx, kind="exchange", resource_id=exchange),
           make_request(ctx, kind="purchase_enquiry", resource_id=sale)]
    assert len(set(ids)) == 3
    assert ctx["client"].get("/api/v1/requests/mine", headers=auth(ctx, "buyer")).json()["data"]["total"] == 3
    assert ctx["client"].get("/api/v1/requests/received", headers=auth(ctx, "owner")).json()["data"]["total"] == 3
    assert ctx["client"].get("/api/v1/requests/mine?page=0", headers=auth(ctx, "buyer")).status_code == 422


@pytest.mark.parametrize("body", [
    {"resource_id": 999, "request_type": "donation", "requested_quantity": 1, "purpose": "Need"},
    {"resource_id": 0, "request_type": "donation", "requested_quantity": 1, "purpose": "Need"},
])
def test_invalid_creation_payloads_are_rejected(request_context, body):
    response = request_context["client"].post("/api/v1/requests", headers=auth(request_context, "buyer"), json=body)
    assert response.status_code in (404, 422)


def test_creation_rejects_wrong_owner_type_stock_and_ineligible_college(request_context):
    ctx = request_context
    owner_resource = add_resource(ctx)
    own_payload = {"resource_id": add_resource(ctx, owner="buyer"), "request_type": "donation",
                   "requested_quantity": 1, "purpose": "Need"}
    assert ctx["client"].post("/api/v1/requests", headers=auth(ctx, "buyer"), json=own_payload).status_code == 403
    bad_type = {"resource_id": owner_resource, "request_type": "purchase_enquiry",
                "requested_quantity": 1, "purpose": "Need"}
    assert ctx["client"].post("/api/v1/requests", headers=auth(ctx, "buyer"), json=bad_type).status_code == 409
    too_many = {"resource_id": owner_resource, "request_type": "donation",
                "requested_quantity": 11, "purpose": "Need"}
    assert ctx["client"].post("/api/v1/requests", headers=auth(ctx, "buyer"), json=too_many).status_code == 409
    assert ctx["client"].post("/api/v1/requests", json=too_many).status_code == 401
    assert ctx["client"].post("/api/v1/requests", headers=auth(ctx, "pending"), json=too_many).status_code == 403
    assert ctx["client"].post("/api/v1/requests", headers=auth(ctx, "rejected"), json=too_many).status_code == 403


def test_approval_partial_rejection_and_request_access_control(request_context):
    ctx = request_context
    resource_id = add_resource(ctx, quantity=10)
    request_id = make_request(ctx, resource_id=resource_id, requested=8)
    response = ctx["client"].post(f"/api/v1/requests/{request_id}/approve", headers=auth(ctx, "owner"),
                                   json={"approved_quantity": 3})
    assert response.status_code == 200, response.text
    assert quantities(ctx, resource_id) == (10, 7, 3)
    assert response.json()["data"]["approved_quantity"] == 3
    assert ctx["client"].post(f"/api/v1/requests/{request_id}/reject", headers=auth(ctx, "owner"),
                               json={"reason": "No longer available"}).status_code == 409
    assert ctx["client"].get(f"/api/v1/requests/{request_id}", headers=auth(ctx, "other")).status_code == 404


def test_rejection_reason_required_and_stored(request_context):
    ctx = request_context
    rid = make_request(ctx)
    assert ctx["client"].post(f"/api/v1/requests/{rid}/reject", headers=auth(ctx, "owner"), json={}).status_code == 422
    response = ctx["client"].post(f"/api/v1/requests/{rid}/reject", headers=auth(ctx, "owner"),
                                   json={"reason": "   "})
    assert response.status_code == 422
    response = ctx["client"].post(f"/api/v1/requests/{rid}/reject", headers=auth(ctx, "owner"),
                                   json={"reason": "Cannot fulfill"})
    assert response.status_code == 200
    assert response.json()["data"]["rejection_reason"] == "Cannot fulfill"
    assert ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "owner"), json={}).status_code == 409


def test_detail_scope_approval_authorization_and_quantity_bounds(request_context):
    ctx = request_context
    resource_id = add_resource(ctx)
    rid = make_request(ctx, resource_id=resource_id, requested=4)
    assert ctx["client"].get(f"/api/v1/requests/{rid}", headers=auth(ctx, "buyer")).status_code == 200
    assert ctx["client"].get(f"/api/v1/requests/{rid}", headers=auth(ctx, "owner")).status_code == 200
    assert ctx["client"].get(f"/api/v1/requests/{rid}", headers=auth(ctx, "other")).status_code == 404
    assert ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "buyer"),
                               json={}).status_code == 403
    too_many = ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "owner"),
                                  json={"approved_quantity": 5})
    assert too_many.status_code == 422
    assert quantities(ctx, resource_id) == (10, 10, 0)
    with ctx["sessions"]() as db:
        assert db.get(Request, rid).status == "pending"


def test_purchase_confirmation_rejects_wrong_college_and_wrong_state(request_context):
    ctx = request_context
    donation_resource = add_resource(ctx)
    donation = make_request(ctx, resource_id=donation_resource)
    assert ctx["client"].post(f"/api/v1/requests/{donation}/purchase-confirmation",
                              headers=auth(ctx, "buyer")).status_code == 409
    sale = add_resource(ctx, kind="sale")
    purchase = make_request(ctx, kind="purchase_enquiry", resource_id=sale)
    assert ctx["client"].post(f"/api/v1/requests/{purchase}/purchase-confirmation",
                              headers=auth(ctx, "buyer")).status_code == 409
    ctx["client"].post(f"/api/v1/requests/{purchase}/approve", headers=auth(ctx, "owner"), json={})
    wrong = ctx["client"].post(f"/api/v1/requests/{purchase}/purchase-confirmation",
                               headers=auth(ctx, "other"))
    assert wrong.status_code == 403
    assert quantities(ctx, sale) == (10, 10, 0)


def test_request_check_constraints_enforce_approved_and_cancellation_fields(request_context):
    ctx = request_context
    rid = make_request(ctx)
    with ctx["sessions"]() as db:
        request = db.get(Request, rid)
        request.approved_quantity = request.requested_quantity + 1
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
        request = db.get(Request, rid)
        request.cancellation_decision = "approved"
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    exchange_rid = make_request(ctx, kind="exchange", requested=5, offered=2)
    with ctx["sessions"]() as db:
        req = db.get(Request, exchange_rid)
        req.approved_quantity = 3
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

    purchase_rid = make_request(ctx, kind="purchase_enquiry", requested=5)
    with ctx["sessions"]() as db:
        req = db.get(Request, purchase_rid)
        req.approved_quantity = 3
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_exchange_approval_atomic_and_partial_rejected(request_context):
    ctx = request_context
    target = add_resource(ctx, kind="exchange", quantity=6)
    offered = add_resource(ctx, owner="buyer", kind="exchange", quantity=4)
    rid = make_request(ctx, kind="exchange", resource_id=target, requested=3, offered_id=offered, offered=2)
    partial = ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "owner"),
                                 json={"approved_quantity": 2})
    assert partial.status_code == 422
    assert quantities(ctx, target) == (6, 6, 0)
    assert quantities(ctx, offered) == (4, 4, 0)
    ctx["client"].patch(f"/api/v1/resources/{offered}/status", headers=auth(ctx, "buyer"), json={"status": "inactive"})
    response = ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "owner"), json={})
    assert response.status_code == 409
    assert quantities(ctx, target) == (6, 6, 0)
    assert quantities(ctx, offered) == (4, 4, 0)


def test_purchase_confirmation_success_duplicate_and_insufficient(request_context):
    ctx = request_context
    stock = add_resource(ctx, kind="sale", quantity=5)
    rid = make_request(ctx, kind="purchase_enquiry", resource_id=stock, requested=4)
    assert ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "owner"), json={}).status_code == 200
    assert quantities(ctx, stock) == (5, 5, 0)
    response = ctx["client"].post(f"/api/v1/requests/{rid}/purchase-confirmation", headers=auth(ctx, "buyer"))
    assert response.status_code == 200
    assert response.json()["data"]["purchase_confirmed_by_user_id"] == ctx["ids"]["buyer"]
    assert quantities(ctx, stock) == (5, 1, 4)
    assert ctx["client"].post(f"/api/v1/requests/{rid}/purchase-confirmation", headers=auth(ctx, "buyer")).status_code == 409

    short = add_resource(ctx, owner="other", kind="sale", quantity=2)
    rid2 = make_request(ctx, kind="purchase_enquiry", resource_id=short, requested=2)
    ctx["client"].post(f"/api/v1/requests/{rid2}/approve", headers=auth(ctx, "other"), json={})
    # Another buyer request consumes stock after approval but before confirmation.
    competing = make_request(ctx, kind="purchase_enquiry", resource_id=short, requested=2)
    ctx["client"].post(f"/api/v1/requests/{competing}/approve", headers=auth(ctx, "other"), json={})
    ctx["client"].post(f"/api/v1/requests/{competing}/purchase-confirmation", headers=auth(ctx, "buyer"))
    failed = ctx["client"].post(f"/api/v1/requests/{rid2}/purchase-confirmation", headers=auth(ctx, "buyer"))
    assert failed.status_code == 409 and failed.json()["error"]["code"] == "insufficient_stock"
    assert quantities(ctx, short) == (2, 0, 2)
    with ctx["sessions"]() as db:
        req = db.get(Request, rid2)
        assert req.status == "awaiting_resolution" and req.purchase_intent_confirmed_at is not None


def test_cancellation_review_releases_or_preserves_exact_reservation(request_context):
    ctx = request_context
    resource_id = add_resource(ctx, quantity=10)
    rid = make_request(ctx, resource_id=resource_id, requested=5)
    ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "owner"), json={})
    assert quantities(ctx, resource_id) == (10, 5, 5)
    submit = ctx["client"].post(f"/api/v1/requests/{rid}/cancel", headers=auth(ctx, "buyer"),
                                 json={"reason": "Plans changed"})
    assert submit.status_code == 200 and quantities(ctx, resource_id) == (10, 5, 5)
    assert ctx["client"].post(f"/api/v1/requests/{rid}/cancel", headers=auth(ctx, "buyer"),
                               json={"reason": "Again"}).status_code == 409
    denied = ctx["client"].post(f"/api/v1/requests/{rid}/cancellation-decision",
                                headers=auth(ctx, "other"), json={"decision": "approved"})
    assert denied.status_code == 403
    rejected = ctx["client"].post(f"/api/v1/requests/{rid}/cancellation-decision",
                                  headers=auth(ctx, "owner"), json={"decision": "rejected"})
    assert rejected.status_code == 200
    assert rejected.json()["data"]["status"] == "approved"
    assert quantities(ctx, resource_id) == (10, 5, 5)
    # A reviewed rejection is retained, and a second cancellation is prevented.
    assert ctx["client"].post(f"/api/v1/requests/{rid}/cancel", headers=auth(ctx, "buyer"),
                               json={"reason": "Again"}).status_code == 409

    rid2 = make_request(ctx, resource_id=resource_id, requested=2)
    ctx["client"].post(f"/api/v1/requests/{rid2}/approve", headers=auth(ctx, "owner"), json={})
    ctx["client"].post(f"/api/v1/requests/{rid2}/cancel", headers=auth(ctx, "buyer"), json={"reason": "Stop"})
    approved = ctx["client"].post(f"/api/v1/requests/{rid2}/cancellation-decision",
                                  headers=auth(ctx, "owner"), json={"decision": "approved"})
    assert approved.status_code == 200 and approved.json()["data"]["status"] == "cancelled"
    assert quantities(ctx, resource_id) == (10, 5, 5)
    assert ctx["client"].post(f"/api/v1/requests/{rid2}/cancellation-decision",
                               headers=auth(ctx, "owner"), json={"decision": "approved"}).status_code == 409


def test_exchange_cancellation_releases_both_sides_and_transfer_blocks(request_context):
    ctx = request_context
    target = add_resource(ctx, kind="exchange", quantity=8)
    offered = add_resource(ctx, owner="buyer", kind="exchange", quantity=8)
    rid = make_request(ctx, kind="exchange", resource_id=target, requested=3, offered_id=offered, offered=2)
    ctx["client"].post(f"/api/v1/requests/{rid}/approve", headers=auth(ctx, "owner"), json={})
    ctx["client"].post(f"/api/v1/requests/{rid}/cancel", headers=auth(ctx, "buyer"), json={"reason": "Stop"})
    result = ctx["client"].post(f"/api/v1/requests/{rid}/cancellation-decision", headers=auth(ctx, "owner"),
                                json={"decision": "approved"})
    assert result.status_code == 200
    assert quantities(ctx, target) == (8, 8, 0)
    assert quantities(ctx, offered) == (8, 8, 0)

    rid2 = make_request(ctx)
    with ctx["sessions"].begin() as db:
        req = db.get(Request, rid2)
        transfer = Transfer(request_id=req.id, resource_id=req.resource_id, transfer_leg="requested_resource",
                            source_college_id=ctx["college_ids"]["owner"],
                            destination_college_id=ctx["college_ids"]["buyer"], quantity=1,
                            dispute_status="none", created_by_user_id=ctx["ids"]["owner"], status="preparing")
        db.add(transfer)
    blocked = ctx["client"].post(f"/api/v1/requests/{rid2}/cancel", headers=auth(ctx, "buyer"),
                                 json={"reason": "Stop"})
    assert blocked.status_code == 409 and blocked.json()["error"]["code"] == "transfers_exist"


def test_concurrent_approvals_use_independent_sqlite_sessions(request_context):
    ctx = request_context
    resource_id = add_resource(ctx, quantity=10)
    reqs = [make_request(ctx, resource_id=resource_id, requested=7),
            make_request(ctx, resource_id=resource_id, requested=7)]

    def approve_one(request_id):
        with ctx["sessions"]() as db:
            actor = db.get(User, ctx["ids"]["owner"])
            try:
                approve_request(db, actor=actor, request_id=request_id, approved_quantity=None)
                return "approved"
            except APIError as exc:
                assert exc.status_code == 409
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(approve_one, reqs))
    assert sorted(outcomes) == ["approved", "conflict"]
    assert quantities(ctx, resource_id) == (10, 3, 7)
    with ctx["sessions"]() as db:
        statuses = list(db.scalars(select(Request.status).where(Request.id.in_(reqs))))
        assert sorted(statuses) == ["approved", "pending"]


def test_purchase_confirmation_revalidates_resource_active_and_sale_type(request_context):
    ctx = request_context
    # 6. Reject confirmation when the resource is no longer active
    sale_stock = add_resource(ctx, kind="sale", quantity=5)
    rid1 = make_request(ctx, kind="purchase_enquiry", resource_id=sale_stock, requested=3)
    ctx["client"].post(f"/api/v1/requests/{rid1}/approve", headers=auth(ctx, "owner"), json={})
    assert quantities(ctx, sale_stock) == (5, 5, 0)

    # Deactivate the resource after approval
    ctx["client"].patch(f"/api/v1/resources/{sale_stock}/status", headers=auth(ctx, "owner"), json={"status": "inactive"})

    # Attempt confirmation
    resp1 = ctx["client"].post(f"/api/v1/requests/{rid1}/purchase-confirmation", headers=auth(ctx, "buyer"))
    assert resp1.status_code == 409
    assert resp1.json()["error"]["code"] == "resource_unavailable"

    # 8. Verify failed confirmation leaves inventory unchanged
    assert quantities(ctx, sale_stock) == (5, 5, 0)

    # 9. Verify failed confirmation does not set metadata or alter status
    with ctx["sessions"]() as db:
        req1 = db.get(Request, rid1)
        assert req1.status == "approved"
        assert req1.purchase_intent_confirmed_at is None
        assert req1.purchase_confirmed_by_user_id is None

    # 7. Reject confirmation when the resource is no longer listed as sale
    sale_stock2 = add_resource(ctx, kind="sale", quantity=5)
    rid2 = make_request(ctx, kind="purchase_enquiry", resource_id=sale_stock2, requested=3)
    ctx["client"].post(f"/api/v1/requests/{rid2}/approve", headers=auth(ctx, "owner"), json={})

    # Mutate resource in DB directly to simulate transfer_type change
    with ctx["sessions"].begin() as db:
        db.get(Resource, sale_stock2).transfer_type = "donation"

    resp2 = ctx["client"].post(f"/api/v1/requests/{rid2}/purchase-confirmation", headers=auth(ctx, "buyer"))
    assert resp2.status_code == 409
    assert resp2.json()["error"]["code"] == "resource_unavailable"

    # 8. Inventory unchanged
    assert quantities(ctx, sale_stock2) == (5, 5, 0)

    # 9. No confirmation metadata or status change
    with ctx["sessions"]() as db:
        req2 = db.get(Request, rid2)
        assert req2.status == "approved"
        assert req2.purchase_intent_confirmed_at is None
        assert req2.purchase_confirmed_by_user_id is None
