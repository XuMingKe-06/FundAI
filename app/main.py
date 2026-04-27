"""
FundAI 后端服务主入口
"""
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import async_engine, Base
from app.core.redis_client import redis_client
from app.api import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    print(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")

    # 创建数据库表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield
    
    # 关闭时
    print(f"关闭 {settings.APP_NAME}")
    await redis_client.close()


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description="多智能体场外基金分析决策系统API",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)


# 请求中间件
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """添加请求上下文"""
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # 处理请求
    response = await call_next(request)
    
    # 添加响应头
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{(time.time() - start_time) * 1000:.2f}ms"
    
    return response


# 异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    return JSONResponse(
        status_code=500,
        content={
            "code": 500,
            "message": "服务器内部错误",
            "error": {
                "type": type(exc).__name__,
                "details": [{"message": str(exc)}]
            },
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": str(uuid.uuid4())
        }
    )


# 注册API路由
app.include_router(api_v1_router, prefix="/api")


# 健康检查
@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION
    }


# 根路径
@app.get("/")
async def root():
    """根路径"""
    return {
        "message": f"欢迎使用{settings.APP_NAME} API",
        "docs": "/docs",
        "health": "/health"
    }
