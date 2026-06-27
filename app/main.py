from fastapi import FastAPI
from app.routes.relationship import router as relationship_router
from app.database import Base, engine
from app.models.asset import Asset
from app.routes.asset import router as asset_router
from app.models.relationship import Relationship
from app.utils.error_handlers import register_exception_handlers

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Asset Management API",
    version="1.0.0"
)

register_exception_handlers(app)

app.include_router(asset_router)
app.include_router(relationship_router)

@app.get("/")
def root():
    return {
        "message": "Asset Management System is running successfully"
    }