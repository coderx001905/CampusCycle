from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.db.session import create_database_engine, get_db
from app.main import create_app
from app.models import Base, College, Request, Resource, Transfer, User


@pytest.fixture
def analytics_ctx(tmp_path: Path):
    db_file = tmp_path / "test_analytics.sqlite3"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        jwt_secret_key="analytics-test-jwt-secret-key-with-sufficient-length",
        csrf_secret_key="analytics-test-csrf-secret-key-with-sufficient-length",
        cors_origins=["http://localhost:5173"],
    )

    with sessions.begin() as db:
        colleges = {
            "col_a": College(name="College Alpha", address="1 Alpha Rd", city="City A", contact_email="a@example.edu", verification_status="verified"),
            "col_b": College(name="College Beta", address="2 Beta Rd", city="City B", contact_email="b@example.edu", verification_status="verified"),
            "col_c": College(name="College Gamma", address="3 Gamma Rd", city="City C", contact_email="c@example.edu", verification_status="verified"),
            "col_pending": College(name="College Pending", address="4 Pending Rd", city="City P", contact_email="p@example.edu", verification_status="pending"),
            "col_rejected": College(name="College Rejected", address="5 Rejected Rd", city="City R", contact_email="r@example.edu", verification_status="rejected"),
        }
        db.add_all(colleges.values())
        db.flush()

        users = {
            "rep_a": User(name="Rep Alpha", email="rep-a@example.edu", password_hash="hash", role="college_representative", college_id=colleges["col_a"].id, is_active=True),
            "rep_b": User(name="Rep Beta", email="rep-b@example.edu", password_hash="hash", role="college_representative", college_id=colleges["col_b"].id, is_active=True),
            "rep_c": User(name="Rep Gamma", email="rep-c@example.edu", password_hash="hash", role="college_representative", college_id=colleges["col_c"].id, is_active=True),
            "admin": User(name="Platform Admin", email="admin@example.edu", password_hash="hash", role="platform_admin", college_id=None, is_active=True),
        }
        db.add_all(users.values())
        db.flush()

        user_ids = {k: u.id for k, u in users.items()}
        college_ids = {k: c.id for k, c in colleges.items()}

    def override_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    client = TestClient(app)
    client.__enter__()

    tokens = {
        k: create_access_token(subject=str(uid), role=users[k].role, college_id=users[k].college_id, settings=settings)
        for k, uid in user_ids.items()
    }

    ctx = {
        "client": client,
        "sessions": sessions,
        "user_ids": user_ids,
        "college_ids": college_ids,
        "tokens": tokens,
    }

    try:
        yield ctx
    finally:
        client.__exit__(None, None, None)
        app.dependency_overrides.clear()
        engine.dispose()


def auth_hdr(ctx, key):
    return {"Authorization": f"Bearer {ctx['tokens'][key]}"}


def test_empty_database_analytics(tmp_path: Path):
    """Test analytics when no resources, requests, or transfers exist."""
    db_file = tmp_path / "empty_analytics.sqlite3"
    engine = create_database_engine(f"sqlite:///{db_file.as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        jwt_secret_key="empty-analytics-test-secret-with-entropy",
        csrf_secret_key="empty-analytics-test-csrf-with-entropy",
        cors_origins=["http://localhost:5173"],
    )

    with sessions.begin() as db:
        college = College(name="Solo College", address="Road 1", city="City", contact_email="solo@example.edu", verification_status="verified")
        db.add(college)
        db.flush()
        rep = User(name="Solo Rep", email="solo@example.edu", password_hash="h", role="college_representative", college_id=college.id, is_active=True)
        admin = User(name="Admin", email="admin@example.edu", password_hash="h", role="platform_admin", college_id=None, is_active=True)
        db.add_all([rep, admin])
        db.flush()
        admin_id = admin.id
        rep_id = rep.id
        col_id = college.id

    def override_db():
        session = sessions()
        try:
            yield session
        finally:
            session.close()

    app = create_app()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings

    admin_token = create_access_token(subject=str(admin_id), role="platform_admin", college_id=None, settings=settings)
    rep_token = create_access_token(subject=str(rep_id), role="college_representative", college_id=col_id, settings=settings)

    with TestClient(app) as client:
        # 1. Summary
        res = client.get("/api/v1/analytics/summary", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["scope"] == "global"
        assert data["resources"]["total_listings"] == 0
        assert data["requests"]["total_requests"] == 0
        assert data["transfers"]["total_transfers"] == 0
        assert data["colleges"]["total_colleges"] == 1

        res_rep = client.get("/api/v1/analytics/summary", headers={"Authorization": f"Bearer {rep_token}"})
        assert res_rep.status_code == 200
        rep_data = res_rep.json()["data"]
        assert rep_data["scope"] == "college"
        assert rep_data["college_id"] == col_id
        assert rep_data["colleges"] is None

        # 2. Categories
        res_cat = client.get("/api/v1/analytics/categories", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_cat.status_code == 200
        assert res_cat.json()["data"]["items"] == []
        assert res_cat.json()["data"]["total_categories"] == 0

        # 3. Requests
        res_req = client.get("/api/v1/analytics/requests", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_req.status_code == 200
        assert res_req.json()["data"]["total_requests"] == 0
        assert res_req.json()["data"]["fulfillment_rate"] == 0.0

        # 4. Transfers
        res_trans = client.get("/api/v1/analytics/transfers", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_trans.status_code == 200
        assert res_trans.json()["data"]["total_transfers"] == 0
        assert res_trans.json()["data"]["quantity_metrics"]["total_shipped"] == 0

        # 5. Colleges (Admin only)
        res_col = client.get("/api/v1/analytics/colleges", headers={"Authorization": f"Bearer {admin_token}"})
        assert res_col.status_code == 200
        assert res_col.json()["data"]["total_colleges"] == 1
        assert res_col.json()["data"]["verified_colleges"] == 1
        assert res_col.json()["data"]["colleges_with_active_listings"] == 0
        assert res_col.json()["data"]["top_participating_colleges"][0]["active_listings_count"] == 0

    app.dependency_overrides.clear()
    engine.dispose()


def test_college_analytics_authorization_boundaries(analytics_ctx):
    """Test that GET /analytics/colleges strictly requires platform_admin role."""
    client = analytics_ctx["client"]

    # 1. Unauthenticated request -> 401
    res = client.get("/api/v1/analytics/colleges")
    assert res.status_code == 401

    # 2. College representative -> 403
    res_rep = client.get("/api/v1/analytics/colleges", headers=auth_hdr(analytics_ctx, "rep_a"))
    assert res_rep.status_code == 403
    assert "Platform administrator access is required." in res_rep.json()["error"]["message"]

    # 3. Platform Admin -> 200
    res_admin = client.get("/api/v1/analytics/colleges", headers=auth_hdr(analytics_ctx, "admin"))
    assert res_admin.status_code == 200
    col_data = res_admin.json()["data"]
    assert col_data["total_colleges"] == 5
    assert col_data["verified_colleges"] == 3
    assert col_data["pending_colleges"] == 1
    assert col_data["rejected_colleges"] == 1


def test_resource_and_summary_scoping_and_isolation(analytics_ctx):
    """Test resource metric calculations and strict scoping between colleges."""
    client = analytics_ctx["client"]
    sessions = analytics_ctx["sessions"]
    col_a_id = analytics_ctx["college_ids"]["col_a"]
    col_b_id = analytics_ctx["college_ids"]["col_b"]
    rep_a_id = analytics_ctx["user_ids"]["rep_a"]
    rep_b_id = analytics_ctx["user_ids"]["rep_b"]

    with sessions.begin() as db:
        # College A: 2 active resources, 1 inactive, 1 depleted
        r_a1 = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Physics Lab Kit",
                        category="Lab Equipment", condition="Good", quantity_total=10,
                        quantity_available=7, quantity_reserved=3, unit="sets", transfer_type="donation", status="active")
        r_a2 = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Calculus Textbooks",
                        category="Books", condition="Like New", quantity_total=20,
                        quantity_available=20, quantity_reserved=0, unit="copies", transfer_type="exchange", status="active")
        r_a3 = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Old Projector",
                        category="Electronics", condition="Fair", quantity_total=5,
                        quantity_available=5, quantity_reserved=0, unit="units", transfer_type="sale", status="inactive")
        r_a4 = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Depleted Beakers",
                        category="Lab Equipment", condition="Used", quantity_total=0,
                        quantity_available=0, quantity_reserved=0, unit="pcs", transfer_type="donation", status="depleted")

        # College B: 1 active resource
        r_b1 = Resource(college_id=col_b_id, created_by_user_id=rep_b_id, name="Digital Oscilloscope",
                        category="Electronics", condition="Good", quantity_total=4,
                        quantity_available=4, quantity_reserved=0, unit="units", transfer_type="donation", status="active")

        db.add_all([r_a1, r_a2, r_a3, r_a4, r_b1])

    # 1. Rep A Summary View
    res_a = client.get("/api/v1/analytics/summary", headers=auth_hdr(analytics_ctx, "rep_a"))
    assert res_a.status_code == 200
    data_a = res_a.json()["data"]
    assert data_a["scope"] == "college"
    assert data_a["college_id"] == col_a_id
    assert data_a["colleges"] is None  # Representative does not receive global college metrics

    res_metrics_a = data_a["resources"]
    assert res_metrics_a["total_listings"] == 4
    assert res_metrics_a["active_listings"] == 2
    assert res_metrics_a["inactive_listings"] == 1
    assert res_metrics_a["depleted_listings"] == 1
    assert res_metrics_a["total_quantity"] == 35  # 10 + 20 + 5 + 0
    assert res_metrics_a["available_quantity"] == 32  # 7 + 20 + 5
    assert res_metrics_a["reserved_quantity"] == 3

    # 2. Rep B Summary View
    res_b = client.get("/api/v1/analytics/summary", headers=auth_hdr(analytics_ctx, "rep_b"))
    assert res_b.status_code == 200
    data_b = res_b.json()["data"]
    assert data_b["scope"] == "college"
    assert data_b["college_id"] == col_b_id

    res_metrics_b = data_b["resources"]
    assert res_metrics_b["total_listings"] == 1
    assert res_metrics_b["active_listings"] == 1
    assert res_metrics_b["total_quantity"] == 4
    assert res_metrics_b["available_quantity"] == 4
    assert res_metrics_b["reserved_quantity"] == 0

    # 3. Platform Admin Summary View
    res_admin = client.get("/api/v1/analytics/summary", headers=auth_hdr(analytics_ctx, "admin"))
    assert res_admin.status_code == 200
    data_admin = res_admin.json()["data"]
    assert data_admin["scope"] == "global"
    assert data_admin["colleges"]["total_colleges"] == 5

    res_metrics_admin = data_admin["resources"]
    assert res_metrics_admin["total_listings"] == 5
    assert res_metrics_admin["active_listings"] == 3
    assert res_metrics_admin["total_quantity"] == 39  # 35 + 4
    assert res_metrics_admin["available_quantity"] == 36  # 32 + 4
    assert res_metrics_admin["reserved_quantity"] == 3


def test_category_analytics_aggregation_and_isolation(analytics_ctx):
    """Test category grouping and quantities per authorized scope."""
    client = analytics_ctx["client"]
    sessions = analytics_ctx["sessions"]
    col_a_id = analytics_ctx["college_ids"]["col_a"]
    col_b_id = analytics_ctx["college_ids"]["col_b"]
    rep_a_id = analytics_ctx["user_ids"]["rep_a"]
    rep_b_id = analytics_ctx["user_ids"]["rep_b"]

    with sessions.begin() as db:
        # College A: Books (20), Lab Equipment (15)
        r1 = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Book 1", category="Books",
                      condition="Good", quantity_total=20, quantity_available=20, quantity_reserved=0, unit="pcs", transfer_type="donation", status="active")
        r2 = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Flasks", category="Lab Equipment",
                      condition="Good", quantity_total=15, quantity_available=10, quantity_reserved=5, unit="pcs", transfer_type="donation", status="active")

        # College B: Books (30), Electronics (10)
        r3 = Resource(college_id=col_b_id, created_by_user_id=rep_b_id, name="Book 2", category="Books",
                      condition="Good", quantity_total=30, quantity_available=30, quantity_reserved=0, unit="pcs", transfer_type="donation", status="active")
        r4 = Resource(college_id=col_b_id, created_by_user_id=rep_b_id, name="Multimeter", category="Electronics",
                      condition="Good", quantity_total=10, quantity_available=10, quantity_reserved=0, unit="pcs", transfer_type="donation", status="active")

        db.add_all([r1, r2, r3, r4])

    # 1. Rep A Categories: sees only Books (20) and Lab Equipment (15)
    res_a = client.get("/api/v1/analytics/categories", headers=auth_hdr(analytics_ctx, "rep_a"))
    assert res_a.status_code == 200
    data_a = res_a.json()["data"]
    assert data_a["scope"] == "college"
    assert data_a["total_categories"] == 2
    cat_names_a = [item["category"] for item in data_a["items"]]
    assert "Books" in cat_names_a
    assert "Lab Equipment" in cat_names_a
    assert "Electronics" not in cat_names_a

    books_a = next(i for i in data_a["items"] if i["category"] == "Books")
    assert books_a["total_listings"] == 1
    assert books_a["total_quantity"] == 20

    lab_a = next(i for i in data_a["items"] if i["category"] == "Lab Equipment")
    assert lab_a["reserved_quantity"] == 5
    assert lab_a["available_quantity"] == 10

    # 2. Platform Admin Categories: sees Books (50), Lab Equipment (15), Electronics (10)
    res_admin = client.get("/api/v1/analytics/categories", headers=auth_hdr(analytics_ctx, "admin"))
    assert res_admin.status_code == 200
    data_admin = res_admin.json()["data"]
    assert data_admin["scope"] == "global"
    assert data_admin["total_categories"] == 3

    books_global = next(i for i in data_admin["items"] if i["category"] == "Books")
    assert books_global["total_listings"] == 2
    assert books_global["total_quantity"] == 50  # 20 + 30


def test_request_analytics_statuses_types_and_fulfillment(analytics_ctx):
    """Test request analytics grouping by status, type, and fulfillment rate."""
    client = analytics_ctx["client"]
    sessions = analytics_ctx["sessions"]
    col_a_id = analytics_ctx["college_ids"]["col_a"]
    col_b_id = analytics_ctx["college_ids"]["col_b"]
    col_c_id = analytics_ctx["college_ids"]["col_c"]
    rep_a_id = analytics_ctx["user_ids"]["rep_a"]
    rep_b_id = analytics_ctx["user_ids"]["rep_b"]
    rep_c_id = analytics_ctx["user_ids"]["rep_c"]

    with sessions.begin() as db:
        res_a = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Res A", category="Books",
                         condition="New", quantity_total=50, quantity_available=30, quantity_reserved=20, unit="pcs", transfer_type="donation", status="active")
        res_b = Resource(college_id=col_b_id, created_by_user_id=rep_b_id, name="Res B", category="Books",
                         condition="New", quantity_total=50, quantity_available=50, quantity_reserved=0, unit="pcs", transfer_type="donation", status="active")
        res_c = Resource(college_id=col_c_id, created_by_user_id=rep_c_id, name="Res C (Offered)", category="Books",
                         condition="New", quantity_total=10, quantity_available=10, quantity_reserved=0, unit="pcs", transfer_type="exchange", status="active")
        db.add_all([res_a, res_b, res_c])
        db.flush()

        # Req 1: B requests from A (donation, pending)
        req1 = Request(resource_id=res_a.id, requesting_college_id=col_b_id, requested_by_user_id=rep_b_id,
                       requested_quantity=10, request_type="donation", purpose="Study", status="pending")
        # Req 2: B requests from A (donation, completed)
        req2 = Request(resource_id=res_a.id, requesting_college_id=col_b_id, requested_by_user_id=rep_b_id,
                       requested_quantity=10, approved_quantity=10, request_type="donation", purpose="Labs", status="completed")
        # Req 3: A requests from B (purchase_enquiry, approved)
        req3 = Request(resource_id=res_b.id, requesting_college_id=col_a_id, requested_by_user_id=rep_a_id,
                       requested_quantity=5, approved_quantity=5, request_type="purchase_enquiry", purpose="Purchase", status="approved")
        # Req 4: C requests from B (exchange, rejected)
        req4 = Request(resource_id=res_b.id, requesting_college_id=col_c_id, requested_by_user_id=rep_c_id,
                       offered_resource_id=res_c.id, offered_quantity=2, requested_quantity=2,
                       request_type="exchange", purpose="Exch", status="rejected")

        db.add_all([req1, req2, req3, req4])

    # 1. Rep A Request Analytics:
    # Involves Req 1 (received from B), Req 2 (received from B), Req 3 (sent to B).
    # Does NOT involve Req 4 (between C and B).
    res_a = client.get("/api/v1/analytics/requests", headers=auth_hdr(analytics_ctx, "rep_a"))
    assert res_a.status_code == 200
    data_a = res_a.json()["data"]
    assert data_a["total_requests"] == 3
    assert data_a["sent_count"] == 1
    assert data_a["received_count"] == 2
    assert data_a["total_requested_quantity"] == 25  # 10 + 10 + 5
    assert data_a["total_approved_quantity"] == 15   # 10 + 5
    # Fulfillment rate: 1 completed out of 3 = 33.3%
    assert data_a["fulfillment_rate"] == 33.3

    status_dict_a = {item["status"]: item["count"] for item in data_a["by_status"]}
    assert status_dict_a.get("pending") == 1
    assert status_dict_a.get("completed") == 1
    assert status_dict_a.get("approved") == 1
    assert status_dict_a.get("rejected") is None

    # 2. Platform Admin Request Analytics: sees all 4 requests
    res_admin = client.get("/api/v1/analytics/requests", headers=auth_hdr(analytics_ctx, "admin"))
    assert res_admin.status_code == 200
    data_admin = res_admin.json()["data"]
    assert data_admin["total_requests"] == 4
    status_dict_admin = {item["status"]: item["count"] for item in data_admin["by_status"]}
    assert status_dict_admin["rejected"] == 1
    type_dict_admin = {item["request_type"]: item["count"] for item in data_admin["by_type"]}
    assert type_dict_admin["donation"] == 2
    assert type_dict_admin["purchase_enquiry"] == 1
    assert type_dict_admin["exchange"] == 1


def test_transfer_analytics_batches_and_disputes(analytics_ctx):
    """Test transfer metrics, quantities, and dispute status tracking."""
    client = analytics_ctx["client"]
    sessions = analytics_ctx["sessions"]
    col_a_id = analytics_ctx["college_ids"]["col_a"]
    col_b_id = analytics_ctx["college_ids"]["col_b"]
    col_c_id = analytics_ctx["college_ids"]["col_c"]
    rep_a_id = analytics_ctx["user_ids"]["rep_a"]
    rep_b_id = analytics_ctx["user_ids"]["rep_b"]
    rep_c_id = analytics_ctx["user_ids"]["rep_c"]

    with sessions.begin() as db:
        res = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Shared Gear", category="Tools",
                       condition="Good", quantity_total=100, quantity_available=50, quantity_reserved=50, unit="pcs", transfer_type="donation", status="active")
        db.add(res)
        db.flush()

        req = Request(resource_id=res.id, requesting_college_id=col_b_id, requested_by_user_id=rep_b_id,
                      requested_quantity=50, approved_quantity=50, request_type="donation", purpose="Work", status="in_progress")
        db.add(req)
        db.flush()

        # Batch 1: A -> B, completed (20 shipped, 20 received good)
        t1 = Transfer(request_id=req.id, resource_id=res.id, transfer_leg="requested_resource",
                      source_college_id=col_a_id, destination_college_id=col_b_id,
                      quantity=20, quantity_received_good=20, dispute_status="none",
                      created_by_user_id=rep_a_id, status="completed")

        # Batch 2: A -> B, preparing (15)
        t2 = Transfer(request_id=req.id, resource_id=res.id, transfer_leg="requested_resource",
                      source_college_id=col_a_id, destination_college_id=col_b_id,
                      quantity=15, dispute_status="none", created_by_user_id=rep_a_id, status="preparing")

        # Batch 3: B -> C, disputed (10 shipped, 7 good, 2 damaged, 1 missing, dispute_status=open)
        t3 = Transfer(request_id=req.id, resource_id=res.id, transfer_leg="requested_resource",
                      source_college_id=col_b_id, destination_college_id=col_c_id,
                      quantity=10, quantity_received_good=7, quantity_damaged=2, quantity_missing=1,
                      dispute_status="open", created_by_user_id=rep_b_id, status="disputed")

        db.add_all([t1, t2, t3])

    # 1. Rep A Transfer Analytics:
    # Involves Transfer 1 and Transfer 2 (source=A).
    # Does NOT involve Transfer 3 (source=B, destination=C).
    res_a = client.get("/api/v1/analytics/transfers", headers=auth_hdr(analytics_ctx, "rep_a"))
    assert res_a.status_code == 200
    data_a = res_a.json()["data"]
    assert data_a["total_transfers"] == 2
    assert data_a["outbound_count"] == 2
    assert data_a["inbound_count"] == 0
    assert data_a["quantity_metrics"]["total_shipped"] == 35  # 20 + 15
    assert data_a["quantity_metrics"]["received_good"] == 20
    assert data_a["quantity_metrics"]["damaged"] == 0
    assert data_a["quantity_metrics"]["missing"] == 0
    assert data_a["dispute_metrics"]["total_disputed"] == 0

    # 2. Platform Admin Transfer Analytics:
    # Sees all 3 transfers
    res_admin = client.get("/api/v1/analytics/transfers", headers=auth_hdr(analytics_ctx, "admin"))
    assert res_admin.status_code == 200
    data_admin = res_admin.json()["data"]
    assert data_admin["total_transfers"] == 3
    assert data_admin["quantity_metrics"]["total_shipped"] == 45  # 20 + 15 + 10
    assert data_admin["quantity_metrics"]["received_good"] == 27  # 20 + 7
    assert data_admin["quantity_metrics"]["damaged"] == 2
    assert data_admin["quantity_metrics"]["missing"] == 1
    assert data_admin["dispute_metrics"]["total_disputed"] == 1
    assert data_admin["dispute_metrics"]["open_disputes"] == 1


def test_college_analytics_active_listings_and_transfers(analytics_ctx):
    """Test Platform Admin college analytics metrics and top participating institutions."""
    client = analytics_ctx["client"]
    sessions = analytics_ctx["sessions"]
    col_a_id = analytics_ctx["college_ids"]["col_a"]
    col_b_id = analytics_ctx["college_ids"]["col_b"]
    rep_a_id = analytics_ctx["user_ids"]["rep_a"]
    rep_b_id = analytics_ctx["user_ids"]["rep_b"]

    with sessions.begin() as db:
        res = Resource(college_id=col_a_id, created_by_user_id=rep_a_id, name="Top Item", category="Lab",
                       condition="Good", quantity_total=10, quantity_available=10, quantity_reserved=0, unit="pcs", transfer_type="donation", status="active")
        db.add(res)
        db.flush()

        req = Request(resource_id=res.id, requesting_college_id=col_b_id, requested_by_user_id=rep_b_id,
                      requested_quantity=5, approved_quantity=5, request_type="donation", purpose="Tests", status="completed")
        db.add(req)
        db.flush()

        t = Transfer(request_id=req.id, resource_id=res.id, transfer_leg="requested_resource",
                     source_college_id=col_a_id, destination_college_id=col_b_id,
                     quantity=5, quantity_received_good=5, dispute_status="none",
                     created_by_user_id=rep_a_id, status="completed")
        db.add(t)

    res_col = client.get("/api/v1/analytics/colleges", headers=auth_hdr(analytics_ctx, "admin"))
    assert res_col.status_code == 200
    data = res_col.json()["data"]

    # 1 college with active listings (College A)
    assert data["colleges_with_active_listings"] == 1

    # Both College A (source) and College B (destination) participated in completed transfer
    assert data["colleges_with_completed_transfers"] == 2

    # Top colleges
    top_colleges = data["top_participating_colleges"]
    assert len(top_colleges) == 3  # Verified colleges count (col_a, col_b, col_c)
    top_col_a = next(c for c in top_colleges if c["id"] == col_a_id)
    assert top_col_a["active_listings_count"] == 1
    assert top_col_a["completed_transfers_count"] == 1
