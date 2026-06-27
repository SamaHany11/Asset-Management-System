from datetime import datetime
import json

from sqlalchemy.orm import Session
from fastapi import UploadFile

from app.models.asset import Asset, AssetStatus
from app.models.relationship import Relationship
from app.repositories.asset_repository import AssetRepository
from app.schemas.asset import AssetCreate, AssetUpdate
from app.utils.certificates import get_certificate_status


class AssetService:

    def __init__(self):
        self.repository = AssetRepository()

   
    def create_asset(self, db: Session, asset_data: AssetCreate) -> Asset:

        existing_asset = self.repository.get_by_value(db, asset_data.value)

        if existing_asset:
            existing_asset.last_seen = datetime.utcnow()
            existing_asset.status = AssetStatus.ACTIVE

            existing_asset.tags = list(
                set((existing_asset.tags or []) + asset_data.tags)
            )

            existing_asset.metadata_json = {
                **(existing_asset.metadata_json or {}),
                **asset_data.metadata_json,
            }

            return self.repository.update(db, existing_asset)

        asset = Asset(
            type=asset_data.type,
            value=asset_data.value,
            status=asset_data.status,
            source=asset_data.source,
            tags=asset_data.tags,
            metadata_json=asset_data.metadata_json,
        )

        return self.repository.create(db, asset)

   
    def get_all_assets(
        self, db: Session, asset_type, status, tag, value, skip, limit,
        sort_by="last_seen", sort_order="desc",
    ):
        return self.repository.get_all(
            db=db,
            asset_type=asset_type,
            status=status,
            tag=tag,
            value=value,
            skip=skip,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
        )

   
    def get_certificates_by_status(
        self, db: Session, cert_status: str, skip: int = 0, limit: int = 10,
    ):
      
        certificates = self.repository.get_all_certificates(db)

        matching = [
            cert for cert in certificates
            if get_certificate_status(cert.metadata_json) == cert_status
        ]

        return matching[skip: skip + limit]

    def get_asset_by_id(self, db: Session, asset_id):
        asset = self.repository.get_by_id(db, asset_id)

        if not asset:
            raise ValueError("Asset not found")

        return asset

   
    def update_asset(self, db: Session, asset_id, asset_data: AssetUpdate):

        asset = self.repository.get_by_id(db, asset_id)

        if not asset:
            raise ValueError("Asset not found")

        if asset_data.status is not None:
            asset.status = asset_data.status

        if asset_data.source is not None:
            asset.source = asset_data.source

        if asset_data.tags is not None:
            asset.tags = asset_data.tags

        if asset_data.metadata_json is not None:
            asset.metadata_json = asset_data.metadata_json

        return self.repository.update(db, asset)

   
    def mark_stale(self, db: Session, asset_id):
       
        asset = self.repository.get_by_id(db, asset_id)

        if not asset:
            raise ValueError("Asset not found")

        asset.status = AssetStatus.STALE
        return self.repository.update(db, asset)

   
    def delete_asset(self, db: Session, asset_id):
        asset = self.repository.get_by_id(db, asset_id)

        if not asset:
            raise ValueError("Asset not found")

        self.repository.delete(db, asset)

   
    def _create_relationship(self, db: Session, source_id, target_id, rel_type):

        rel = Relationship(
            source_asset_id=source_id,
            target_asset_id=target_id,
            relationship_type=rel_type,
        )

        db.add(rel)
        db.commit()

   
    async def import_assets(self, db: Session, file: UploadFile):

        content = await file.read()
        data = json.loads(content)

        imported = 0
        updated = 0
        failed = 0

        id_map = {}

        
        for item in data:

            try:
                external_id = item.get("id")

                existing = self.repository.get_by_value(db, item["value"])

                if existing:
                    existing.last_seen = datetime.utcnow()
                    existing.status = AssetStatus.ACTIVE

                    existing.tags = list(
                        set((existing.tags or []) + item.get("tags", []))
                    )

                    existing.metadata_json = {
                        **(existing.metadata_json or {}),
                        **item.get("metadata", {}),
                    }

                    self.repository.update(db, existing)

                    id_map[external_id] = existing.id
                    updated += 1

                else:
                    asset = Asset(
                        type=item["type"],
                        value=item["value"],
                        status=AssetStatus(item.get("status", "active")),
                        source=item.get("source", "import"),
                        tags=item.get("tags", []),
                        metadata_json=item.get("metadata", {}),
                    )

                    created = self.repository.create(db, asset)

                    id_map[external_id] = created.id
                    imported += 1

            except Exception:
                failed += 1

       
        for item in data:

            try:
                src_id = id_map.get(item.get("id"))
                if not src_id:
                    continue

                if item.get("parent"):
                    target_id = id_map.get(item["parent"])
                    if target_id:
                        self._create_relationship(db, src_id, target_id, "parent")

                if item.get("covers"):
                    target_id = id_map.get(item["covers"])
                    if target_id:
                        self._create_relationship(db, src_id, target_id, "covers")

            except Exception:
                continue

        return {
            "imported": imported,
            "updated": updated,
            "failed": failed,
        }