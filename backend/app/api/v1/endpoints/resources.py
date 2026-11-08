import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.authorization import get_current_user, require_college_representative
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models import Resource, User
from app.schemas.resources import (
    MarketplaceResource,
    ResourceCreate,
    ResourceImageEnvelope,
    ResourceInventoryItem,
    ResourceStatusUpdate,
    ResourceUpdate,
)
from app.services.resource_images import ImageUploadError, MAX_IMAGE_BYTES, process_uploaded_image
from app.services.resources import (
    browse_resources,
    clear_resource_image,
    create_resource,
    get_owned_resource,
    get_resource_image_path,
    get_visible_resource,
    inventory_data,
    list_owned_inventory,
    marketplace_data,
    replace_resource_image,
    set_listing_status,
    update_resource,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["resources"])


def _response(resource: Resource, settings: Settings) -> dict[str, object]:
    return MarketplaceResource.model_validate(marketplace_data(resource, settings)).model_dump(mode="json")


@router.post("/resources", status_code=201)
def create_resource_listing(payload: ResourceCreate,
                            user: User = Depends(require_college_representative),
                            db: Session = Depends(get_db),
                            settings: Settings = Depends(get_settings)) -> dict:
    resource = create_resource(db, user=user, payload=payload)
    return {"success": True, "data": _response(resource, settings)}


@router.get("/resources")
def list_resources(
    search: str | None = Query(default=None, max_length=200),
    category: str | None = Query(default=None, max_length=100),
    condition: str | None = Query(default=None, max_length=30),
    transfer_type: str | None = Query(default=None, pattern="^(donation|exchange|sale)$"),
    college_id: int | None = Query(default=None, ge=1),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict:
    items, total = browse_resources(
        db, search=search, category=category, condition=condition,
        transfer_type=transfer_type, college_id=college_id,
        page=page, page_size=page_size,
    )
    return {"success": True, "data": {
        "items": [_response(resource, settings) for resource in items],
        "page": page, "page_size": page_size, "total": total,
    }}


@router.get("/resources/{resource_id}")
def resource_details(resource_id: int, user: User = Depends(get_current_user),
                     db: Session = Depends(get_db),
                     settings: Settings = Depends(get_settings)) -> dict:
    resource = get_visible_resource(db, resource_id=resource_id, user=user)
    return {"success": True, "data": _response(resource, settings)}


@router.patch("/resources/{resource_id}")
def edit_resource(resource_id: int, payload: ResourceUpdate,
                  user: User = Depends(require_college_representative),
                  db: Session = Depends(get_db),
                  settings: Settings = Depends(get_settings)) -> dict:
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="Provide at least one descriptive field to update.")
    resource = get_owned_resource(db, resource_id=resource_id, user=user)
    resource = update_resource(db, resource=resource, changes=changes)
    return {"success": True, "data": _response(resource, settings)}


@router.patch("/resources/{resource_id}/status")
def change_resource_status(resource_id: int, payload: ResourceStatusUpdate,
                           user: User = Depends(require_college_representative),
                           db: Session = Depends(get_db),
                           settings: Settings = Depends(get_settings)) -> dict:
    resource = get_owned_resource(db, resource_id=resource_id, user=user)
    resource = set_listing_status(db, resource=resource, requested_status=payload.status)
    return {"success": True, "data": _response(resource, settings)}


@router.get("/inventory/me")
def own_inventory(user: User = Depends(require_college_representative),
                  db: Session = Depends(get_db)) -> dict:
    items = list_owned_inventory(db, user=user)
    return {"success": True, "data": {"items": [
        ResourceInventoryItem.model_validate(inventory_data(resource)).model_dump(mode="json")
        for resource in items
    ], "total": len(items)}}


@router.post("/resources/{resource_id}/image", status_code=200,
             response_model=ResourceImageEnvelope)
async def upload_resource_image(resource_id: int, file: UploadFile = File(...),
                                user: User = Depends(require_college_representative),
                                db: Session = Depends(get_db),
                                settings: Settings = Depends(get_settings)) -> dict:
    resource = get_owned_resource(db, resource_id=resource_id, user=user)
    try:
        content = await file.read(MAX_IMAGE_BYTES + 1)
    finally:
        await file.close()
    try:
        processed = process_uploaded_image(content, filename=file.filename,
                                           content_type=file.content_type)
    except ImageUploadError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    replace_resource_image(db, resource=resource, image=processed, settings=settings)
    return {"success": True, "data": {
        "resource_id": resource.id,
        "image_url": f"/api/v1/resources/{resource.id}/image",
        "media_type": processed.media_type,
        "size_bytes": len(processed.content),
    }}


@router.get("/resources/{resource_id}/image")
def serve_resource_image(resource_id: int, user: User = Depends(get_current_user),
                         db: Session = Depends(get_db),
                         settings: Settings = Depends(get_settings)) -> FileResponse:
    resource = get_visible_resource(db, resource_id=resource_id, user=user)
    image = get_resource_image_path(db, resource=resource, settings=settings)
    if image is None:
        raise HTTPException(status_code=404, detail="Resource image not found.")
    path, media_type = image
    return FileResponse(path, media_type=media_type,
                        filename=f"resource-{resource.id}{path.suffix}",
                        headers={"X-Content-Type-Options": "nosniff",
                                 "Cache-Control": "private, max-age=3600"})


@router.delete("/resources/{resource_id}/image")
def remove_resource_image(resource_id: int,
                          user: User = Depends(require_college_representative),
                          db: Session = Depends(get_db),
                          settings: Settings = Depends(get_settings)) -> dict:
    resource = get_owned_resource(db, resource_id=resource_id, user=user)
    clear_resource_image(db, resource=resource, settings=settings)
    return {"success": True, "data": {"resource_id": resource.id, "image_url": None}}
