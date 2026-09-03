"""Aggregated v2 API router."""

from fastapi import APIRouter

from app.api.v2 import workspaces, folders, assets, search, health

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(workspaces.router)
api_router.include_router(folders.router)
api_router.include_router(assets.router)
api_router.include_router(search.router)
