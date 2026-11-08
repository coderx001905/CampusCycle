from fastapi import APIRouter

from app.api.v1.endpoints import accounts, auth, health, requests, resources, transfers

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(accounts.router)
api_router.include_router(resources.router)
api_router.include_router(requests.router)
api_router.include_router(transfers.router)
