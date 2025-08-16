"""
API Router Aggregator for Smart-0DTE-System v1 API

This module aggregates all v1 API routers into a single router
for inclusion in the main FastAPI application.
"""

from fastapi import APIRouter

from . import market_data, reporting

api_router = APIRouter()

# Include all v1 routers
api_router.include_router(market_data.router)
api_router.include_router(reporting.router)

