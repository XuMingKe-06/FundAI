"""
FundAI 后端服务主入口
"""
import time
import uuid
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logger import setup_logging, get_request_logger

# 在所有其他模块导入之前初始化日志系统
# 这样后续导入的模块（database、cache、api 等）中使用 logging.getLogger()
# 或 from loguru import logger 的日志都会被正确拦截并写入文件
setup_logging(
    console_level="DEBUG" if settings.DEBUG else "INFO",
    file_level="DEBUG",
    error_level="ERROR",
    debug_mode=settings.DEBUG,
)

from loguru import logger

# 以下模块的导入在日志系统初始化之后，确保其导入期日志能写入文件
from app.core.database import async_engine, Base
from app.core.cache import cache_client
from app.api import api_v1_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info("启动 {} v{}", settings.APP_NAME, settings.APP_VERSION)
    logger.info("DEBUG 模式: {}", settings.DEBUG)

    # 创建数据库表
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表初始化完成")

    yield

    # 关闭时
    logger.info("关闭 {}", settings.APP_NAME)
    await cache_client.close()
    logger.info("Redis 缓存连接已关闭")


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
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept"],
    max_age=3600,
)


# 请求中间件
@app.middleware("http")
async def add_request_context(request: Request, call_next):
    """添加请求上下文，记录请求日志并注入 request_id"""
    request_id = str(uuid.uuid4())
    start_time = time.time()

    # 获取带 request_id 的日志记录器
    req_logger = get_request_logger(request_id)

    # 记录请求开始
    req_logger.info(
        "请求开始 | {} {} | client={}",
        request.method,
        request.url.path,
        request.client.host if request.client else "unknown"
    )

    # 处理请求
    response = await call_next(request)

    # 计算响应时间
    duration_ms = (time.time() - start_time) * 1000

    # 添加响应头
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

    # 记录请求完成
    req_logger.info(
        "请求完成 | {} {} | status={} | duration={:.2f}ms",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms
    )

    return response


# 异常处理
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理，确保统一的错误响应格式"""
    request_id = str(uuid.uuid4())
    logger.warning(
        "HTTP异常 | request_id={} | status={} | path={} | detail={}",
        request_id, exc.status_code, request.url.path, exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "request_id": request_id
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理，生产环境不泄露内部错误详情"""
    request_id = str(uuid.uuid4())
    logger.exception(
        "未处理异常 | request_id={} | path={} | error={}: {}",
        request_id, request.url.path, type(exc).__name__, exc
    )
    content = {
        "code": 500,
        "message": "服务器内部错误",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "request_id": request_id
    }
    # 仅在 DEBUG 模式下暴露错误类型和详情
    if settings.DEBUG:
        content["error"] = {
            "type": type(exc).__name__,
            "details": [{"message": str(exc)}]
        }
    return JSONResponse(status_code=500, content=content)


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
