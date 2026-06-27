from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional, Literal
from uuid import UUID

from app.database import get_db
from app.schemas.asset import AssetCreate, AssetResponse, AssetUpdate, ImportResponse
from app.services.asset_service import AssetService
from app.services.relationship_service import RelationshipService
from app.models.asset import AssetType, AssetStatus
from app.utils.auth import verify_api_key

router = APIRouter(
    prefix="/assets",
    tags=["Assets"]
)

service = AssetService()
relationship_service = RelationshipService()


@router.post(
    "",
    response_model=AssetResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
)
def create_asset(
    asset: AssetCreate,
    db: Session = Depends(get_db)
):
    return service.create_asset(db, asset)


@router.post(
    "/import",
    response_model=ImportResponse,
    dependencies=[Depends(verify_api_key)],
)
async def bulk_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    return await service.import_assets(db, file)


@router.get("", response_model=List[AssetResponse])
def get_all_assets(
    type: Optional[AssetType] = None,
    status: Optional[AssetStatus] = None,
    tag: Optional[str] = None,
    value: Optional[str] = None,
    skip: int = 0,
    limit: int = 10,
    sort_by: Literal["value", "first_seen", "last_seen", "status", "type"] = "last_seen",
    sort_order: Literal["asc", "desc"] = "desc",
    db: Session = Depends(get_db),
):
    return service.get_all_assets(
        db=db,
        asset_type=type,
        status=status,
        tag=tag,
        value=value,
        skip=skip,
        limit=limit,
        sort_by=sort_by,
        sort_order=sort_order,
    )

@router.get("/certificates", response_model=List[AssetResponse])
def get_certificates_by_lifecycle_status(
    cert_status: Literal["expired", "expiring_soon", "valid"],
    skip: int = 0,
    limit: int = 10,
    db: Session = Depends(get_db),
):
   
    return service.get_certificates_by_status(
        db=db, cert_status=cert_status, skip=skip, limit=limit,
    )


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(asset_id: UUID, db: Session = Depends(get_db)):
    try:
        return service.get_asset_by_id(db, asset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{asset_id}/graph")
def get_asset_with_relationships(asset_id: UUID, db: Session = Depends(get_db)):
   
    try:
        asset = service.get_asset_by_id(db, asset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    relationships = relationship_service.get_relationships(db, asset_id)

    related = []
    for rel in relationships:
        other = (
            rel.target_asset if rel.source_asset_id == asset_id else rel.source_asset
        )
        related.append({
            "relationship_type": rel.relationship_type,
            "direction": "outgoing" if rel.source_asset_id == asset_id else "incoming",
            "asset": AssetResponse.model_validate(other),
        })

    return {
        "asset": AssetResponse.model_validate(asset),
        "related": related,
    }


@router.put(
    "/{asset_id}",
    response_model=AssetResponse,
    dependencies=[Depends(verify_api_key)],
)
def update_asset(
    asset_id: UUID,
    asset: AssetUpdate,
    db: Session = Depends(get_db),
):
    try:
        return service.update_asset(db, asset_id, asset)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post(
    "/{asset_id}/mark-stale",
    response_model=AssetResponse,
    dependencies=[Depends(verify_api_key)],
)
def mark_asset_stale(asset_id: UUID, db: Session = Depends(get_db)):
   
    try:
        return service.mark_stale(db, asset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete(
    "/{asset_id}",
    status_code=204,
    dependencies=[Depends(verify_api_key)],
)
def delete_asset(asset_id: UUID, db: Session = Depends(get_db)):
    try:
        service.delete_asset(db, asset_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))