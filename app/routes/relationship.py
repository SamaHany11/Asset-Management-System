from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.relationship import (
    RelationshipCreate,
    RelationshipResponse,
)
from app.services.relationship_service import RelationshipService
from app.utils.auth import verify_api_key

router = APIRouter(
    prefix="/relationships",
    tags=["Relationships"],
)

service = RelationshipService()


@router.post(
    "",
    response_model=RelationshipResponse,
    status_code=201,
    dependencies=[Depends(verify_api_key)],
)
def create_relationship(
    relationship: RelationshipCreate,
    db: Session = Depends(get_db),
):
    try:
        return service.create_relationship(db, relationship)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/{asset_id}",
    response_model=list[RelationshipResponse],
)
def get_relationships(
    asset_id: UUID,
    db: Session = Depends(get_db),
):
    return service.get_relationships(db, asset_id)