"""
集中日志配置模块

基于 loguru 实现统一的日志管理，通过 InterceptHandler 拦截标准库 logging 的输出，
使所有使用 logging.getLogger() 的模块自动纳入 loguru 的格式化和文件输出。

特性：
- 控制台彩色输出（精简格式，便于开发调试）
- 文件详细输出（完整格式，包含模块/函数/行号，便于问题排查）
- 每次启动覆盖上次日志（开发环境友好）
- 独立的 ERROR 级别日志文件
- 请求上下文追踪（request_id）
- 自动拦截 uvicorn/fastapi/sqlalchemy 等第三方库的日志
"""
import logging
import os
import sys
from pathlib import Path
from typing import Optional

from loguru import logger


# 日志文件根目录（项目根目录下的 log/）
LOG_DIR = Path(os.getcwd()) / "log"

# 日志文件路径
LOG_FILE = LOG_DIR / "fundai.log"
ERROR_LOG_FILE = LOG_DIR / "fundai_error.log"

# 控制台日志格式（彩色，精简）
CONSOLE_FORMAT = (
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
    "<level>{message}</level>"
)

# 文件日志格式模板
# 注意：loguru 格式字符串不支持 .get() 方法调用，
# 且 {extra[request_id]} 在 request_id 不存在时会抛出 KeyError 导致日志丢失，
# 因此使用自定义格式化函数 _file_format_func 在渲染前注入默认值
FILE_FORMAT = (
    "{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
    "{name}:{function}:{line} | "
    "{extra[request_id]} | "
    "{message}\n"
)


def _file_format_func(record: dict) -> str:
    """
    文件日志自定义格式化函数

    在渲染前将 request_id 的默认值注入到 record["extra"] 中，
    确保模板中的 {extra[request_id]} 不会因 KeyError 而丢失日志。

    Args:
        record: loguru 日志记录字典

    Returns:
        日志格式模板字符串
    """
    record["extra"].setdefault("request_id", "")
    return FILE_FORMAT


class InterceptHandler(logging.Handler):
    """
    标准库 logging 拦截器

    将标准库 logging 的所有日志记录转发给 loguru，
    从而实现统一的格式化和输出管理。
    所有使用 logging.getLogger(__name__) 的模块无需修改代码即可受益。
    """

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 跳过 loguru 自身的日志，避免无限递归
        if record.name.startswith("loguru."):
            return

        frame, depth = logging.currentframe(), 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )


def _ensure_log_dir() -> None:
    """确保日志目录存在"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _remove_default_loguru_handlers() -> None:
    """移除 loguru 默认的控制台处理器（ID=0），避免重复输出"""
    logger.remove()


def _add_console_handler(level: str = "DEBUG") -> None:
    """
    添加控制台日志处理器

    Args:
        level: 最低日志级别，默认 DEBUG
    """
    logger.add(
        sys.stderr,
        format=CONSOLE_FORMAT,
        level=level,
        colorize=True,
        diagnose=True,
    )


def _add_file_handler(level: str = "DEBUG") -> None:
    """
    添加文件日志处理器（覆盖模式）

    每次应用启动时覆盖上次的日志文件，确保日志内容属于当前运行。
    使用 enqueue=True 确保线程安全写入，并在进程退出时排空队列刷新到磁盘。

    Args:
        level: 最低日志级别，默认 DEBUG
    """
    _ensure_log_dir()
    logger.add(
        str(LOG_FILE),
        format=_file_format_func,
        level=level,
        mode="w",
        encoding="utf-8",
        diagnose=True,
        backtrace=True,
        enqueue=True,
    )


def _add_error_file_handler(level: str = "ERROR") -> None:
    """
    添加错误日志文件处理器（覆盖模式）

    仅记录 ERROR 及以上级别的日志到单独的错误日志文件。
    使用 enqueue=True 确保线程安全写入，并在进程退出时排空队列刷新到磁盘。

    Args:
        level: 最低日志级别，默认 ERROR
    """
    _ensure_log_dir()
    logger.add(
        str(ERROR_LOG_FILE),
        format=_file_format_func,
        level=level,
        mode="w",
        encoding="utf-8",
        diagnose=True,
        backtrace=True,
        enqueue=True,
    )


def _intercept_standard_logging(level: int = logging.DEBUG, debug_mode: bool = True) -> None:
    """
    拦截标准库 logging，将所有日志转发给 loguru

    通过设置 root logger 的处理器为 InterceptHandler，
    并调整关键第三方库的日志级别，避免过于冗余的输出。

    Args:
        level: 拦截的最低日志级别，默认 DEBUG
        debug_mode: 是否为调试模式，影响 SQLAlchemy 等第三方库的日志级别
    """
    intercept_handler = InterceptHandler()

    # 配置 root logger
    root_logger = logging.getLogger()
    root_logger.handlers = [intercept_handler]
    root_logger.setLevel(level)

    # 拦截 uvicorn 日志（避免启动时重复输出）
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(logger_name)
        uvicorn_logger.handlers = [intercept_handler]
        uvicorn_logger.propagate = False

    # 拦截 FastAPI 日志
    fastapi_logger = logging.getLogger("fastapi")
    fastapi_logger.handlers = [intercept_handler]
    fastapi_logger.propagate = False

    # SQLAlchemy 日志拦截：替换其自有 handler 为 InterceptHandler
    # echo=True 时 SQLAlchemy 会给 sqlalchemy.engine 添加 StreamHandler，
    # 导致控制台双输出且日志不经过 loguru 文件处理器。
    # 解决方案：将所有 sqlalchemy 子日志器的 handler 替换为 InterceptHandler，
    # 并设置 propagate=False 防止重复传播到 root logger。
    for sa_name in ("sqlalchemy", "sqlalchemy.engine", "sqlalchemy.pool"):
        sa_logger = logging.getLogger(sa_name)
        sa_logger.handlers = [intercept_handler]
        sa_logger.propagate = False
    # sqlalchemy 父日志器级别设为 WARNING，避免大量 SQL 调试日志
    sqlalchemy_logger = logging.getLogger("sqlalchemy")
    sqlalchemy_logger.setLevel(logging.WARNING)
    # sqlalchemy.engine：调试模式下保留 INFO 级别（可见 SQL 语句），
    # 生产模式下设为 WARNING（仅记录警告）
    sqlalchemy_engine_logger = logging.getLogger("sqlalchemy.engine")
    sqlalchemy_engine_logger.setLevel(logging.INFO if debug_mode else logging.WARNING)
    # sqlalchemy.pool 设为 WARNING，连接池细节无需记录
    sqlalchemy_pool_logger = logging.getLogger("sqlalchemy.pool")
    sqlalchemy_pool_logger.setLevel(logging.WARNING)

    # httpx/httpcore 日志级别设为 WARNING（避免大量 HTTP 请求日志）
    for http_logger_name in ("httpx", "httpcore"):
        http_logger = logging.getLogger(http_logger_name)
        http_logger.setLevel(logging.WARNING)

    # openai 日志级别设为 WARNING
    openai_logger = logging.getLogger("openai")
    openai_logger.setLevel(logging.WARNING)

    # chromadb 日志级别设为 WARNING
    chromadb_logger = logging.getLogger("chromadb")
    chromadb_logger.setLevel(logging.WARNING)

    # watchfiles 日志级别设为 WARNING（避免 --reload 时大量 "change detected" 噪音）
    watchfiles_logger = logging.getLogger("watchfiles.main")
    watchfiles_logger.setLevel(logging.WARNING)


def setup_logging(
    console_level: str = "DEBUG",
    file_level: str = "DEBUG",
    error_level: str = "ERROR",
    debug_mode: bool = True,
) -> None:
    """
    初始化日志系统

    应在应用启动时尽早调用（在 main.py 中，其他业务模块导入之前）。
    配置 loguru 的控制台和文件输出，并拦截标准库 logging。

    Args:
        console_level: 控制台最低日志级别，默认 DEBUG
        file_level: 文件最低日志级别，默认 DEBUG
        error_level: 错误日志文件最低日志级别，默认 ERROR
        debug_mode: 是否为调试模式，影响第三方库日志级别（如 SQLAlchemy）
    """
    # 移除 loguru 默认处理器
    _remove_default_loguru_handlers()

    # 添加自定义处理器
    _add_console_handler(console_level)
    _add_file_handler(file_level)
    _add_error_file_handler(error_level)

    # 拦截标准库 logging
    _intercept_standard_logging(debug_mode=debug_mode)

    logger.info("日志系统初始化完成 | 控制台级别={} | 文件级别={} | 错误级别={}", console_level, file_level, error_level)
    logger.info("日志文件路径: {} | {}", LOG_FILE, ERROR_LOG_FILE)


def get_request_logger(request_id: Optional[str] = None) -> logger.__class__:
    """
    获取带有请求上下文的日志记录器

    在请求处理中间件中使用，将 request_id 绑定到日志上下文，
    使同一请求的所有日志行都携带相同的 request_id，便于追踪。

    Args:
        request_id: 请求唯一标识，为 None 时使用空字符串

    Returns:
        绑定了 request_id 上下文的 loguru logger
    """
    return logger.bind(request_id=request_id or "")
