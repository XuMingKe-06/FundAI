"""
API V1 路由
"""
from fastapi import APIRouter

from app.api.v1.endpoints import funds, analysis, sessions, knowledge, settings

router = APIRouter(prefix="/v1")

# 注册各模块路由
router.include_router(funds.router)
router.include_router(analysis.router)
router.include_router(sessions.router)
router.include_router(knowledge.router)
router.include_router(settings.router)
