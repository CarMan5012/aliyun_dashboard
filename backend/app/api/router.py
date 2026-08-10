from fastapi import APIRouter
from app.api.v1 import accounts, resources, settings

api_router = APIRouter()

# 挂载账号管理路由，前缀为 /accounts
api_router.include_router(accounts.router, prefix="/accounts", tags=["accounts"])

# 挂载资源及检索等路由，前缀为空（直接位于 v1 根路径下）
api_router.include_router(resources.router, tags=["resources"])
api_router.include_router(settings.router, prefix="/settings", tags=["settings"])
