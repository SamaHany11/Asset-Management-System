from sqlalchemy.orm import Session

from app.models.relationship import Relationship


class RelationshipRepository:

    def create(self, db: Session, relationship: Relationship):
        db.add(relationship)
        db.commit()
        db.refresh(relationship)
        return relationship

    def get_all_for_asset(self, db: Session, asset_id):
        return (
            db.query(Relationship)
            .filter(
                (Relationship.source_asset_id == asset_id)
                | (Relationship.target_asset_id == asset_id)
            )
            .all()
        )