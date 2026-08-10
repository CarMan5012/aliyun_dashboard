import time
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import OperationalError
from app.core.config import settings
from app.api.router import api_router
from app.db.base import Base
from app.db.session import engine
from app.db.db_migration import migrate_db

# 初始化日志
logger = logging.getLogger("app.main")
logging.basicConfig(level=logging.INFO)

# 初始化 FastAPI 实例
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc"
)

# 自动在 MySQL 中建表（如果不存在对应表），带有重试逻辑防止 MySQL 启动过慢导致进程直接崩溃
def init_db():
    max_retries = 30
    retry_interval = 2
    for i in range(max_retries):
        try:
            logger.info(f"Connecting to database at {settings.MYSQL_HOST}:{settings.MYSQL_PORT} (attempt {i+1}/{max_retries})...")
            Base.metadata.create_all(bind=engine)
            logger.info("Successfully connected to the database and initialized tables.")
            # 执行平滑增量迁移与孤立数据审计
            migrate_db()
            return
        except OperationalError as e:
            if i < max_retries - 1:
                logger.warning(f"Database connection failed, retrying in {retry_interval} seconds... error: {e}")
                time.sleep(retry_interval)
            else:
                logger.error("Database connection failed after maximum retries. Exiting.")
                raise e

import os
if os.getenv("TESTING") != "true":
    init_db()

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由总线，统一前缀为 /api/v1
app.include_router(api_router, prefix=settings.API_V1_STR)

from fastapi import Request
from fastapi.responses import JSONResponse

@app.exception_handler(OperationalError)
async def db_operational_exception_handler(request: Request, exc: OperationalError):
    return JSONResponse(
        status_code=503,
        content={"detail": f"数据库连接故障: {str(exc)}"}
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    err_str = str(exc)
    if "OperationalError" in err_str or "MySQL" in err_str:
        return JSONResponse(
            status_code=503,
            content={"detail": f"数据库连接或查询故障: {err_str}"}
        )
    return JSONResponse(
        status_code=500,
        content={"detail": err_str}
    )

@app.get("/")
def read_root():
    return {"message": "阿里云资源看板 API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
