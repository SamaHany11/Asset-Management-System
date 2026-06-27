import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Column, String, DateTime, Enum as SqlEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY

from app.database import Base


class AssetType(str, Enum):
    DOMAIN = "domain"
    SUBDOMAIN = "subdomain"
    IP_ADDRESS = "ip_address"
    SERVICE = "service"
    CERTIFICATE = "certificate"
    TECHNOLOGY = "technology"


class AssetStatus(str, Enum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    type = Column(SqlEnum(AssetType), nullable=False)

    value = Column(String, nullable=False, unique=True)

    status = Column(
        SqlEnum(AssetStatus),
        nullable=False,
        default=AssetStatus.ACTIVE
    )

    first_seen = Column(
        DateTime,
        default=datetime.utcnow
    )

    last_seen = Column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    source = Column(String)

    tags = Column(ARRAY(String))

    metadata_json = Column(JSONB, default=dict)