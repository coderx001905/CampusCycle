import io
import struct
import zlib
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.db.session import create_database_engine, get_db
from app.main import create_app
from app.models import Base, College, Request, Resource, User
from app.services.resource_images import (
    ImageUploadError,
    MAX_IMAGE_BYTES,
    MAX_IMAGE_DIMENSION,
    MAX_IMAGE_PIXELS,
    MAX_MULTIPART_OVERHEAD_BYTES,
    ProcessedImage,
    process_uploaded_image,
    store_processed_image,
)
from app.services.resources import replace_resource_image, synchronize_depleted_status


@pytest.fixture
def resource_context(tmp_path: Path):
    image_root = tmp_path / "resource images"
    engine = create_database_engine(f"sqlite:///{(tmp_path / 'resources.sqlite3').as_posix()}")
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    settings = Settings(
        _env_file=None,
        jwt_secret_key="phase-six-test-jwt-secret-has-32-bytes-000",
        csrf_secret_key="phase-six-test-csrf-secret-has-32-bytes-000",
        resource_image_dir=image_root,
        cors_origins=["http://localhost:5173"],
    )
    with sessions.begin() as db:
        verified = College(name="North College", address="1 North Road", city="Pune",
                           contact_email="north-office@example.edu", verification_status="verified")
        other = College(name="South College", address="2 South Road", city="Mumbai",
                        contact_email="south-office@example.edu", verification_status="verified")
        pending = College(name="Pending College", address="3 Road", city="Delhi",
                          contact_email="pending-office@example.edu", verification_status="pending")
        rejected = College(name="Rejected College", address="4 Road", city="Jaipur",
                           contact_email="rejected-office@example.edu", verification_status="rejected")
        db.add_all([verified, other, pending, rejected])
        db.flush()
        owner = User(name="North Rep", email="north-rep@example.edu", password_hash="test-hash",
                     role="college_representative", college_id=verified.id, is_active=True)
        other_rep = User(name="South Rep", email="south-rep@example.edu", password_hash="test-hash",
                         role="college_representative", college_id=other.id, is_active=True)
        pending_rep = User(name="Pending Rep", email="pending-rep@example.edu", password_hash="test-hash",
                           role="college_representative", college_id=pending.id, is_active=True)
        rejected_rep = User(name="Rejected Rep", email="rejected-rep@example.edu", password_hash="test-hash",
                            role="college_representative", college_id=rejected.id, is_active=True)
        admin = User(name="Platform Admin", email="platform-admin@example.edu", password_hash="test-hash",
                     role="platform_admin", college_id=None, is_active=True)
        db.add_all([owner, other_rep, pending_rep, rejected_rep, admin])
        db.flush()
        users = {"owner": owner, "other": other_rep, "pending": pending_rep,
                 "rejected": rejected_rep, "admin": admin}
        colleges = {"owner": verified, "other": other, "pending": pending, "rejected": rejected}
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
        key: create_access_token(subject=str(user_id), role=users[key].role,
                                 college_id=users[key].college_id, settings=settings)
        for key, user_id in ids.items()
    }
    try:
        yield {"app": app, "client": client, "sessions": sessions, "settings": settings,
               "image_root": image_root, "user_ids": ids, "college_ids": college_ids,
               "tokens": tokens}
    finally:
        client.__exit__(None, None, None)
        app.dependency_overrides.clear()
        engine.dispose()


def headers(context, role="owner"):
    return {"Authorization": f"Bearer {context['tokens'][role]}"}


def resource_payload(**overrides):
    payload = {
        "name": "Calculus Textbook",
        "description": "First year mathematics textbook",
        "category": "Books",
        "condition": "Good, lightly used",
        "quantity": 8,
        "unit": "copies",
        "transfer_type": "donation",
        "indicative_price": None,
    }
    payload.update(overrides)
    return payload


def create_resource(context, role="owner", **overrides):
    return context["client"].post("/api/v1/resources", headers=headers(context, role),
                                  json=resource_payload(**overrides))


def make_image(fmt: str, *, color=(20, 120, 40)) -> bytes:
    content = io.BytesIO()
    Image.new("RGB", (8, 6), color).save(content, format=fmt)
    return content.getvalue()


def png_with_dimensions(width: int, height: int) -> bytes:
    content = bytearray(make_image("PNG"))
    content[16:24] = struct.pack(">II", width, height)
    content[29:33] = struct.pack(">I", zlib.crc32(content[12:29]) & 0xFFFFFFFF)
    return bytes(content)


def upload(context, resource_id: int, *, content: bytes | None = None,
           filename: str = "campus.png", content_type: str = "image/png", role="owner"):
    return context["client"].post(
        f"/api/v1/resources/{resource_id}/image", headers=headers(context, role),
        files={"file": (filename, content if content is not None else make_image("PNG"), content_type)},
    )


def test_resource_creation_sets_server_owned_fields_and_initial_inventory(resource_context):
    context = resource_context
    response = create_resource(context)
    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["quantity_available"] == 8
    assert data["status"] == "active"
    assert "quantity_total" not in data and "quantity_reserved" not in data
    with context["sessions"]() as db:
        resource = db.get(Resource, data["id"])
        assert resource.college_id == context["college_ids"]["owner"]
        assert resource.created_by_user_id == context["user_ids"]["owner"]
        assert (resource.quantity_total, resource.quantity_available, resource.quantity_reserved) == (8, 8, 0)
        assert resource.status == "active"


@pytest.mark.parametrize("role", ["pending", "rejected"])
def test_pending_and_rejected_colleges_cannot_create_but_can_browse(resource_context, role):
    context = resource_context
    assert create_resource(context, role=role).status_code == 403
    response = context["client"].get("/api/v1/resources", headers=headers(context, role))
    assert response.status_code == 200


def test_platform_admin_cannot_create_resource_and_browsing_requires_auth(resource_context):
    context = resource_context
    assert create_resource(context, role="admin").status_code == 403
    assert context["client"].get("/api/v1/resources").status_code == 401


@pytest.mark.parametrize("extra", [
    {"college_id": 999}, {"created_by_user_id": 999}, {"status": "depleted"},
    {"quantity_total": 500}, {"quantity_available": 400}, {"quantity_reserved": 10},
    {"image_path": "../../outside.png"},
])
def test_create_rejects_server_managed_field_injection(resource_context, extra):
    payload = resource_payload(**extra)
    response = resource_context["client"].post("/api/v1/resources", headers=headers(resource_context), json=payload)
    assert response.status_code == 422


@pytest.mark.parametrize("changes", [
    {"quantity": 0}, {"quantity": -2}, {"name": " "}, {"category": ""},
    {"condition": "x" * 31}, {"unit": "x" * 51}, {"transfer_type": "rental"},
    {"indicative_price": -0.01}, {"indicative_price": "1.234"},
])
def test_create_rejects_invalid_resource_values(resource_context, changes):
    response = create_resource(resource_context, **changes)
    assert response.status_code == 422


def test_sale_price_is_optional_and_category_condition_are_not_fixed_enums(resource_context):
    response = create_resource(resource_context, transfer_type="sale", category="Rare lab supplies",
                               condition="Custom condition descriptor", indicative_price=None)
    assert response.status_code == 201, response.text
    assert response.json()["data"]["indicative_price"] is None


def test_marketplace_search_filters_pagination_and_inventory_privacy(resource_context):
    context = resource_context
    first = create_resource(context, name="Physics Guide", description="Thermal science reference",
                            category="Textbooks", condition="Used", transfer_type="donation")
    second = create_resource(context, name="Chemistry Set", description="Organic lab equipment",
                             category="Equipment", condition="New", transfer_type="exchange")
    third = create_resource(context, role="other", name="Physics Workbook", description="Practice exercises",
                            category="Textbooks", condition="Used", transfer_type="sale")
    assert first.status_code == second.status_code == third.status_code == 201
    search_name = context["client"].get("/api/v1/resources?search=physics", headers=headers(context, "pending"))
    search_description = context["client"].get("/api/v1/resources?search=organic", headers=headers(context))
    combined = context["client"].get(
        f"/api/v1/resources?category=Textbooks&condition=Used&transfer_type=donation&college_id={context['college_ids']['owner']}",
        headers=headers(context, "rejected"),
    )
    page = context["client"].get("/api/v1/resources?page=1&page_size=1", headers=headers(context))
    assert len(search_name.json()["data"]["items"]) == 2
    assert len(search_description.json()["data"]["items"]) == 1
    assert len(combined.json()["data"]["items"]) == 1
    assert combined.json()["data"]["items"][0]["id"] == first.json()["data"]["id"]
    assert (page.json()["data"]["page"], page.json()["data"]["page_size"], page.json()["data"]["total"]) == (1, 1, 3)
    item = page.json()["data"]["items"][0]
    assert item["quantity_available"] == 8
    assert "quantity_total" not in item and "quantity_reserved" not in item
    assert "created_by_user_id" not in item and "image_path" not in item


@pytest.mark.parametrize("query", ["?page=0", "?page_size=0", "?page_size=101", "?transfer_type=rent"])
def test_marketplace_rejects_invalid_filters_and_pagination(resource_context, query):
    response = resource_context["client"].get("/api/v1/resources" + query, headers=headers(resource_context))
    assert response.status_code == 422


def test_inactive_and_depleted_resources_are_hidden_except_from_owner(resource_context):
    context = resource_context
    active = create_resource(context)
    inactive = create_resource(context, name="Private Inactive Listing")
    depleted = create_resource(context, name="Private Depleted Listing")
    with context["sessions"].begin() as db:
        db.get(Resource, inactive.json()["data"]["id"]).status = "inactive"
        row = db.get(Resource, depleted.json()["data"]["id"])
        row.status = "depleted"
        row.quantity_total = 0
        row.quantity_available = 0
        row.quantity_reserved = 0
    listing = context["client"].get("/api/v1/resources", headers=headers(context, "other"))
    assert [item["id"] for item in listing.json()["data"]["items"]] == [active.json()["data"]["id"]]
    assert context["client"].get(f"/api/v1/resources/{inactive.json()['data']['id']}", headers=headers(context, "other")).status_code == 404
    owner_detail = context["client"].get(f"/api/v1/resources/{inactive.json()['data']['id']}", headers=headers(context))
    assert owner_detail.status_code == 200 and owner_detail.json()["data"]["status"] == "inactive"
    assert context["client"].get(f"/api/v1/resources/{depleted.json()['data']['id']}", headers=headers(context, "admin")).status_code == 404
    assert context["client"].get("/api/v1/resources/99999", headers=headers(context)).status_code == 404


def test_resource_edit_only_changes_approved_descriptive_fields(resource_context):
    context = resource_context
    created = create_resource(context)
    resource_id = created.json()["data"]["id"]
    response = context["client"].patch(f"/api/v1/resources/{resource_id}", headers=headers(context),
                                        json={"name": "Updated name", "description": None,
                                              "category": "Supplies", "indicative_price": "12.50"})
    assert response.status_code == 200, response.text
    assert response.json()["data"]["name"] == "Updated name"
    assert response.json()["data"]["description"] is None
    assert response.json()["data"]["indicative_price"] == "12.50"
    with context["sessions"]() as db:
        resource = db.get(Resource, resource_id)
        assert (resource.quantity_total, resource.quantity_available, resource.quantity_reserved) == (8, 8, 0)


@pytest.mark.parametrize("injected", [
    {"id": 999}, {"college_id": 999}, {"created_by_user_id": 999},
    {"quantity_total": 999}, {"quantity_available": 999}, {"quantity_reserved": 0},
    {"status": "inactive"}, {"created_at": "2020-01-01T00:00:00Z"},
    {"updated_at": "2020-01-01T00:00:00Z"}, {"image_path": "evil.png"},
    {"unknown_field": "value"},
])
def test_resource_edit_rejects_server_managed_and_unknown_fields(resource_context, injected):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    response = context["client"].patch(f"/api/v1/resources/{resource_id}", headers=headers(context), json=injected)
    assert response.status_code == 422


def test_resource_edit_enforces_owner_role_and_valid_values(resource_context):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    url = f"/api/v1/resources/{resource_id}"
    assert context["client"].patch(url, headers=headers(context, "other"), json={"name": "x"}).status_code == 404
    assert context["client"].patch(url, headers=headers(context, "admin"), json={"name": "x"}).status_code == 403
    assert context["client"].patch(url, headers=headers(context), json={"indicative_price": -1}).status_code == 422
    assert context["client"].patch(url, headers=headers(context), json={"name": None}).status_code == 422
    assert context["client"].patch(url, headers=headers(context), json={}).status_code == 422


def test_transfer_type_change_rejected_when_referenced_by_outstanding_request(resource_context):
    context = resource_context
    res_id = create_resource(context, transfer_type="sale").json()["data"]["id"]
    with context["sessions"].begin() as db:
        req = Request(
            resource_id=res_id,
            requesting_college_id=context["college_ids"]["other"],
            requested_by_user_id=context["user_ids"]["other"],
            requested_quantity=2,
            request_type="purchase_enquiry",
            purpose="Need books for class",
            status="pending",
        )
        db.add(req)

    url = f"/api/v1/resources/{res_id}"
    resp = context["client"].patch(url, headers=headers(context), json={"transfer_type": "donation"})
    assert resp.status_code == 409
    assert "outstanding requests" in resp.json()["error"]["message"]

    # Permit unrelated resource-field updates even when a request references the resource
    unrelated = context["client"].patch(url, headers=headers(context), json={"name": "Updated Title", "description": "New description"})
    assert unrelated.status_code == 200
    assert unrelated.json()["data"]["name"] == "Updated Title"

    # Also permit update if transfer_type is sent unchanged
    same_type = context["client"].patch(url, headers=headers(context), json={"transfer_type": "sale", "name": "Same Type Title"})
    assert same_type.status_code == 200
    assert same_type.json()["data"]["name"] == "Same Type Title"


def test_transfer_type_change_rejected_when_referenced_as_offered_resource(resource_context):
    context = resource_context
    offered_res_id = create_resource(context, transfer_type="exchange").json()["data"]["id"]
    target_res_id = create_resource(context, role="other", transfer_type="exchange").json()["data"]["id"]

    with context["sessions"].begin() as db:
        req = Request(
            resource_id=target_res_id,
            requesting_college_id=context["college_ids"]["owner"],
            requested_by_user_id=context["user_ids"]["owner"],
            offered_resource_id=offered_res_id,
            requested_quantity=1,
            offered_quantity=1,
            request_type="exchange",
            purpose="Exchange textbook",
            status="pending",
        )
        db.add(req)

    url = f"/api/v1/resources/{offered_res_id}"
    resp = context["client"].patch(url, headers=headers(context), json={"transfer_type": "donation"})
    assert resp.status_code == 409
    assert "outstanding requests" in resp.json()["error"]["message"]


def test_transfer_type_change_rejected_when_quantity_reserved(resource_context):
    context = resource_context
    res_id = create_resource(context, transfer_type="donation").json()["data"]["id"]
    with context["sessions"].begin() as db:
        res = db.get(Resource, res_id)
        res.quantity_reserved = 2
        res.quantity_available = res.quantity_total - 2

    url = f"/api/v1/resources/{res_id}"
    resp = context["client"].patch(url, headers=headers(context), json={"transfer_type": "sale"})
    assert resp.status_code == 409
    assert "reserved" in resp.json()["error"]["message"]


def test_transfer_type_change_permitted_without_outstanding_requests_or_reservations(resource_context):
    context = resource_context
    res_id = create_resource(context, transfer_type="donation").json()["data"]["id"]

    # Even if historical inactive requests (completed/rejected/cancelled) exist
    with context["sessions"].begin() as db:
        for status in ("rejected", "completed", "cancelled"):
            db.add(Request(
                resource_id=res_id,
                requesting_college_id=context["college_ids"]["other"],
                requested_by_user_id=context["user_ids"]["other"],
                requested_quantity=1,
                request_type="donation",
                purpose="Historical request",
                status=status,
            ))

    url = f"/api/v1/resources/{res_id}"
    resp = context["client"].patch(url, headers=headers(context), json={"transfer_type": "sale"})
    assert resp.status_code == 200
    assert resp.json()["data"]["transfer_type"] == "sale"
    with context["sessions"]() as db:
        assert db.get(Resource, res_id).transfer_type == "sale"


def test_status_changes_preserve_quantities_and_enforce_ownership(resource_context):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    url = f"/api/v1/resources/{resource_id}/status"
    inactive = context["client"].patch(url, headers=headers(context), json={"status": "inactive"})
    assert inactive.status_code == 200 and inactive.json()["data"]["status"] == "inactive"
    active = context["client"].patch(url, headers=headers(context), json={"status": "active"})
    assert active.status_code == 200 and active.json()["data"]["status"] == "active"
    assert context["client"].patch(url, headers=headers(context, "other"), json={"status": "inactive"}).status_code == 404
    assert context["client"].patch(url, headers=headers(context, "admin"), json={"status": "inactive"}).status_code == 403
    assert context["client"].patch(url, headers=headers(context), json={"status": "depleted"}).status_code == 422
    with context["sessions"]() as db:
        resource = db.get(Resource, resource_id)
        assert (resource.quantity_total, resource.quantity_available, resource.quantity_reserved) == (8, 8, 0)


def test_zero_available_with_reserved_stock_is_not_depleted(resource_context):
    context = resource_context
    resource_id = create_resource(context, quantity=3).json()["data"]["id"]
    with context["sessions"].begin() as db:
        resource = db.get(Resource, resource_id)
        resource.quantity_total = 3
        resource.quantity_available = 0
        resource.quantity_reserved = 3
        synchronize_depleted_status(resource)
    with context["sessions"]() as db:
        resource = db.get(Resource, resource_id)
        assert resource.status == "active"
        assert (resource.quantity_total, resource.quantity_available, resource.quantity_reserved) == (3, 0, 3)


def test_zero_physical_stock_becomes_depleted_and_requires_stock_before_reactivation(resource_context):
    context = resource_context
    resource_id = create_resource(context, quantity=1).json()["data"]["id"]
    with context["sessions"].begin() as db:
        resource = db.get(Resource, resource_id)
        resource.quantity_total = 0
        resource.quantity_available = 0
        resource.quantity_reserved = 0
        synchronize_depleted_status(resource)
    with context["sessions"]() as db:
        assert db.get(Resource, resource_id).status == "depleted"
    url = f"/api/v1/resources/{resource_id}/status"
    assert context["client"].patch(url, headers=headers(context), json={"status": "active"}).status_code == 409
    with context["sessions"].begin() as db:
        resource = db.get(Resource, resource_id)
        resource.quantity_total = 1
        resource.quantity_available = 1
        resource.quantity_reserved = 0
    reactivated = context["client"].patch(url, headers=headers(context), json={"status": "active"})
    assert reactivated.status_code == 200 and reactivated.json()["data"]["status"] == "active"


def test_inventory_endpoint_is_owner_scoped_and_separate_from_marketplace(resource_context):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    with context["sessions"].begin() as db:
        resource = db.get(Resource, resource_id)
        resource.quantity_available = 6
        resource.quantity_reserved = 2
    inventory = context["client"].get("/api/v1/inventory/me", headers=headers(context))
    assert inventory.status_code == 200
    owned = inventory.json()["data"]["items"][0]
    assert owned["quantity_total"] == 8 and owned["quantity_reserved"] == 2
    marketplace = context["client"].get("/api/v1/resources", headers=headers(context, "other"))
    item = marketplace.json()["data"]["items"][0]
    assert item["quantity_available"] == 6
    assert "quantity_reserved" not in item and "quantity_total" not in item
    assert context["client"].get("/api/v1/inventory/me", headers=headers(context, "pending")).status_code == 403
    assert context["client"].get("/api/v1/inventory/me", headers=headers(context, "admin")).status_code == 403


@pytest.mark.parametrize(("fmt", "filename", "media_type"), [
    ("JPEG", "cover.jpg", "image/jpeg"),
    ("PNG", "cover.png", "image/png"),
    ("WEBP", "cover.webp", "image/webp"),
])
def test_valid_raster_formats_upload_serve_and_reencode_without_metadata(resource_context, fmt, filename, media_type):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    response = upload(context, resource_id, content=make_image(fmt), filename=filename, content_type=media_type)
    assert response.status_code == 200, response.text
    result = response.json()["data"]
    assert result["media_type"] == media_type
    assert "resource_image_dir" not in response.text and str(context["image_root"]) not in response.text
    with context["sessions"]() as db:
        resource = db.get(Resource, resource_id)
        reference = resource.image_path
        path = context["image_root"] / reference
        assert path.is_file() and Path(reference).name == reference
        with Image.open(path) as saved:
            assert saved.format == fmt
            # Pillow reports format-level metadata for JPEG/WebP even after
            # re-encoding. User-provided metadata must be stripped.
            assert not {"exif", "icc_profile", "xmp", "comment"}.intersection(saved.info)
    served = context["client"].get(f"/api/v1/resources/{resource_id}/image", headers=headers(context, "other"))
    assert served.status_code == 200 and served.headers["content-type"] == media_type


@pytest.mark.parametrize(("filename", "content_type", "content"), [
    ("bad.gif", "image/gif", b"GIF89a"),
    ("spoof.jpg", "image/jpeg", make_image("PNG")),
    ("spoof.png", "image/jpeg", make_image("PNG")),
    ("broken.png", "image/png", b"not an image"),
    ("../outside.png", "image/png", make_image("PNG")),
    ("..\\outside.png", "image/png", make_image("PNG")),
])
def test_unsupported_spoofed_malformed_and_path_injected_uploads_are_rejected(
    resource_context, filename, content_type, content
):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    response = upload(context, resource_id, content=content, filename=filename, content_type=content_type)
    assert response.status_code in {415, 422}
    assert not context["image_root"].exists()


def test_oversized_upload_is_rejected_before_image_processing(resource_context):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    response = upload(context, resource_id, content=b"x" * (MAX_IMAGE_BYTES + 1))
    assert response.status_code == 413
    assert not context["image_root"].exists()


def test_multipart_request_size_limit_is_streamed_before_authentication_and_without_content_length(resource_context):
    context = resource_context
    boundary = "resource-image-audit-boundary"
    prefix = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="large.png"\r\n'
        "Content-Type: image/png\r\n\r\n"
    ).encode()
    body = prefix + b"x" * (MAX_IMAGE_BYTES + MAX_MULTIPART_OVERHEAD_BYTES + 1) + f"\r\n--{boundary}--\r\n".encode()
    chunks = (body[index:index + 64 * 1024] for index in range(0, len(body), 64 * 1024))
    request = context["client"].build_request(
        "POST", "/api/v1/resources/1/image",
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        content=chunks,
    )
    assert "content-length" not in request.headers
    response = context["client"].send(request)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"
    assert not context["image_root"].exists()


@pytest.mark.parametrize(("width", "height"), [
    (MAX_IMAGE_DIMENSION + 1, 1),
    (4_000, 4_000),
])
def test_image_pixel_and_dimension_limits_reject_before_full_decode(width, height):
    with pytest.raises(ImageUploadError) as error:
        process_uploaded_image(
            png_with_dimensions(width, height),
            filename="large.png",
            content_type="image/png",
        )
    assert error.value.status_code == 413
    assert width > MAX_IMAGE_DIMENSION or height > MAX_IMAGE_DIMENSION or width * height > MAX_IMAGE_PIXELS


def test_image_upload_and_removal_enforce_owner_scope(resource_context):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    assert upload(context, resource_id, role="other").status_code == 404
    assert upload(context, resource_id, role="admin").status_code == 403
    assert context["client"].delete(f"/api/v1/resources/{resource_id}/image", headers=headers(context, "other")).status_code == 404
    assert context["client"].delete(f"/api/v1/resources/{resource_id}/image", headers=headers(context, "admin")).status_code == 403


def test_image_replacement_and_removal_clean_up_files_and_reference(resource_context):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    first = upload(context, resource_id)
    assert first.status_code == 200
    with context["sessions"]() as db:
        resource = db.get(Resource, resource_id)
        first_path = context["image_root"] / resource.image_path
        first_reference = resource.image_path
    second = upload(context, resource_id, content=make_image("JPEG"),
                    filename="replacement.jpg", content_type="image/jpeg")
    assert second.status_code == 200
    with context["sessions"]() as db:
        resource = db.get(Resource, resource_id)
        second_path = context["image_root"] / resource.image_path
        assert resource.image_path != first_reference
        assert second_path.is_file() and not first_path.exists()
    removed = context["client"].delete(f"/api/v1/resources/{resource_id}/image", headers=headers(context))
    assert removed.status_code == 200 and removed.json()["data"]["image_url"] is None
    assert not second_path.exists()
    with context["sessions"]() as db:
        assert db.get(Resource, resource_id).image_path is None


def test_database_failure_during_replacement_preserves_old_image_and_removes_new_file(resource_context, monkeypatch):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    assert upload(context, resource_id).status_code == 200
    with context["sessions"]() as db:
        original_reference = db.get(Resource, resource_id).image_path
    def fail_commit(_self):
        raise RuntimeError("database write failed")
    monkeypatch.setattr(Session, "commit", fail_commit)
    response = upload(context, resource_id, content=make_image("JPEG"),
                       filename="replacement.jpg", content_type="image/jpeg")
    assert response.status_code == 500
    with context["sessions"]() as db:
        assert db.get(Resource, resource_id).image_path == original_reference
    assert list(context["image_root"].glob("*.jpg")) == []
    assert len(list(context["image_root"].glob("*.png"))) == 1


def test_database_failure_during_removal_preserves_existing_image(resource_context, monkeypatch):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    assert upload(context, resource_id).status_code == 200
    with context["sessions"]() as db:
        reference = db.get(Resource, resource_id).image_path
    def fail_commit(_self):
        raise RuntimeError("database write failed")
    monkeypatch.setattr(Session, "commit", fail_commit)
    response = context["client"].delete(f"/api/v1/resources/{resource_id}/image", headers=headers(context))
    assert response.status_code == 500
    assert (context["image_root"] / reference).is_file()
    with context["sessions"]() as db:
        assert db.get(Resource, resource_id).image_path == reference


def test_concurrent_image_replacements_use_conditional_reference_update(resource_context):
    context = resource_context
    resource_id = create_resource(context).json()["data"]["id"]
    assert upload(context, resource_id).status_code == 200
    first_session = context["sessions"]()
    second_session = context["sessions"]()
    try:
        first_resource = first_session.get(Resource, resource_id)
        second_resource = second_session.get(Resource, resource_id)
        assert first_resource.image_path == second_resource.image_path
        first_image = ProcessedImage(make_image("JPEG"), "jpg", "image/jpeg")
        second_image = ProcessedImage(make_image("WEBP"), "webp", "image/webp")
        replace_resource_image(first_session, resource=first_resource, image=first_image,
                               settings=context["settings"])
        with pytest.raises(HTTPException) as conflict:
            replace_resource_image(second_session, resource=second_resource, image=second_image,
                                   settings=context["settings"])
        assert conflict.value.status_code == 409
    finally:
        first_session.close()
        second_session.close()
    with context["sessions"]() as db:
        current_reference = db.get(Resource, resource_id).image_path
    files = list(context["image_root"].glob("*.*"))
    assert len(files) == 1
    assert files[0].name == current_reference


def test_storage_root_creation_failure_is_reported_without_unbound_local_error(resource_context, tmp_path):
    blocked_root = tmp_path / "not-a-directory"
    blocked_root.write_text("occupies the configured image directory")
    settings = resource_context["settings"].model_copy(update={"resource_image_dir": blocked_root})
    processed = ProcessedImage(make_image("PNG"), "png", "image/png")
    with pytest.raises(ImageUploadError) as error:
        store_processed_image(processed, settings)
    assert error.value.status_code == 500


def test_openapi_registers_resource_and_inventory_endpoints_and_schema_stays_seven_tables(resource_context):
    context = resource_context
    paths = context["app"].openapi()["paths"]
    assert "/api/v1/resources" in paths
    assert "/api/v1/resources/{resource_id}" in paths
    assert "/api/v1/resources/{resource_id}/status" in paths
    assert "/api/v1/resources/{resource_id}/image" in paths
    assert "/api/v1/inventory/me" in paths
    assert set(Base.metadata.tables) == {
        "colleges", "users", "resources", "requests", "transfers",
        "transfer_status_history", "refresh_tokens",
    }
