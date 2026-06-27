from sqlalchemy.orm import Session

from app.models.relationship import Relationship
from app.repositories.asset_repository import AssetRepository
from app.repositories.relationship_repository import RelationshipRepository
from app.schemas.relationship import RelationshipCreate


class RelationshipService:

    def __init__(self):
        self.repository = RelationshipRepository()
        self.asset_repository = AssetRepository()

    def create_relationship(
        self,
        db: Session,
        relationship_data: RelationshipCreate,
    ):

        source = self.asset_repository.get_by_id(
            db,
            relationship_data.source_asset_id,
        )

        target = self.asset_repository.get_by_id(
            db,
            relationship_data.target_asset_id,
        )

        if not source or not target:
            raise ValueError("Asset not found.")

        relationship = Relationship(
            source_asset_id=relationship_data.source_asset_id,
            target_asset_id=relationship_data.target_asset_id,
            relationship_type=relationship_data.relationship_type,
        )

        return self.repository.create(db, relationship)

    def get_relationships(self, db: Session, asset_id):
        return self.repository.get_all_for_asset(db, asset_id)