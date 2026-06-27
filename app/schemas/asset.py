from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.models.asset import AssetStatus, AssetType
from app.utils.certificates import get_certificate_status


class AssetCreate(BaseModel):
    type: AssetType
    value: str
    status: AssetStatus = AssetStatus.ACTIVE
    source: str
    tags: list[str] = Field(default_factory=list)
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class AssetResponse(BaseModel):
    id: UUID
    type: AssetType
    value: str
    status: AssetStatus
    source: str
    tags: list[str]
    metadata_json: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)

    @computed_field
    @property
    def cert_status(self) -> Optional[str]:
      
        if self.type != AssetType.CERTIFICATE:
            return None
        return get_certificate_status(self.metadata_json)


class AssetUpdate(BaseModel):
    status: AssetStatus | None = None
    source: str | None = None
    tags: list[str] | None = None
    metadata_json: dict[str, Any] | None = None


class ImportResponse(BaseModel):
    imported: int
    updated: int
    failed: int