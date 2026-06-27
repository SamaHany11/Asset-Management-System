from sqlalchemy.orm import Session

from app.models.asset import Asset


class AssetRepository:

    def create(self, db: Session, asset: Asset) -> Asset:
        db.add(asset)
        db.commit()
        db.refresh(asset)
        return asset

    def update(self, db: Session, asset: Asset) -> Asset:
        db.commit()
        db.refresh(asset)
        return asset

    def delete(self, db: Session, asset: Asset) -> None:
        db.delete(asset)
        db.commit()

    def get_by_value(self, db: Session, value: str) -> Asset | None:
        return db.query(Asset).filter(Asset.value == value).first()

    def get_by_id(self, db: Session, asset_id):
        return db.query(Asset).filter(Asset.id == asset_id).first()

    SORTABLE_FIELDS = {
        "value": Asset.value,
        "first_seen": Asset.first_seen,
        "last_seen": Asset.last_seen,
        "status": Asset.status,
        "type": Asset.type,
    }

    def get_all(
        self,
        db: Session,
        asset_type=None,
        status=None,
        tag=None,
        value=None,
        skip: int = 0,
        limit: int = 10,
        sort_by: str = "last_seen",
        sort_order: str = "desc",
    ):
        query = db.query(Asset)

        if asset_type:
            query = query.filter(Asset.type == asset_type)

        if status:
            query = query.filter(Asset.status == status)

        if value:
            query = query.filter(Asset.value.ilike(f"%{value}%"))

        if tag:
            query = query.filter(Asset.tags.any(tag))

        sort_column = self.SORTABLE_FIELDS.get(sort_by, Asset.last_seen)
        if sort_order == "asc":
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())

        return (
            query
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count_all(
        self,
        db: Session,
        asset_type=None,
        status=None,
        tag=None,
        value=None,
    ) -> int:
        query = db.query(Asset)

        if asset_type:
            query = query.filter(Asset.type == asset_type)
        if status:
            query = query.filter(Asset.status == status)
        if value:
            query = query.filter(Asset.value.ilike(f"%{value}%"))
        if tag:
            query = query.filter(Asset.tags.any(tag))

        return query.count()

    def get_all_certificates(self, db: Session):
       
        return db.query(Asset).filter(Asset.type == "certificate").all()