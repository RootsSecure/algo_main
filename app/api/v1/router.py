from fastapi import APIRouter

from app.api.v1.endpoints import alerts, auth, devices, gateway, health, incidents, partners, properties

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth"])
api_router.include_router(properties.router, prefix="/properties", tags=["Properties"])
api_router.include_router(devices.router, prefix="/devices", tags=["Devices"])
api_router.include_router(gateway.router, prefix="/gateway", tags=["Gateway"])
api_router.include_router(alerts.router, prefix="/alerts", tags=["Alerts"])
api_router.include_router(incidents.router, prefix="/incidents", tags=["Incidents"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(partners.router, prefix="/partners", tags=["Partners"])
