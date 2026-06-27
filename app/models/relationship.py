import uuid

from sqlalchemy import Column, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.database import Base


class Relationship(Base):
    __tablename__ = "relationships"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    source_asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assets.id"),
        nullable=False
    )

    target_asset_id = Column(
        UUID(as_uuid=True),
        ForeignKey("assets.id"),
        nullable=False
    )

    relationship_type = Column(
        String,
        nullable=False
    )

    source_asset = relationship(
        "Asset",
        foreign_keys=[source_asset_id]
    )

    target_asset = relationship(
        "Asset",
        foreign_keys=[target_asset_id]
    )