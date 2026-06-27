from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RelationshipCreate(BaseModel):
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: str


class RelationshipResponse(BaseModel):
    id: UUID
    source_asset_id: UUID
    target_asset_id: UUID
    relationship_type: str

    model_config = ConfigDict(from_attributes=True)