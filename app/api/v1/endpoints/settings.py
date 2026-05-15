"""
配置管理API端点
"""
import time
import logging
from fastapi import APIRouter, HTTPException, status

from app.schemas.common import ApiResponse
from app.schemas.settings import (
    LLMSettings,
    DatasourceSettings,
    RAGSettings,
    AllSettings,
    LLMTestRequest,
    LLMTestResponse,
)
from app.core.settings_manager import get_settings_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["配置"])


@router.get("", response_model=ApiResponse[AllSettings])
async def get_all_settings():
    """获取所有配置"""
    sm = get_settings_manager()
    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="success",
        data=AllSettings(
            llm=LLMSettings(**config.get("llm", {})),
            datasource=DatasourceSettings(**config.get("datasource", {})),
            rag=RAGSettings(**config.get("rag", {})),
        ),
    )


@router.put("", response_model=ApiResponse[AllSettings])
async def update_all_settings(data: AllSettings):
    """更新所有配置"""
    sm = get_settings_manager()
    sm.update(data.model_dump())
    
    # 重置 RAG 服务的配置缓存，使其能重新检测 Embedding 配置状态
    from app.services.rag_service import get_rag_service
    get_rag_service().reset_config_cache()
    
    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="配置更新成功",
        data=AllSettings(
            llm=LLMSettings(**config.get("llm", {})),
            datasource=DatasourceSettings(**config.get("datasource", {})),
            rag=RAGSettings(**config.get("rag", {})),
        ),
    )


@router.get("/llm", response_model=ApiResponse[LLMSettings])
async def get_llm_settings():
    """获取LLM配置"""
    sm = get_settings_manager()
    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="success",
        data=LLMSettings(**config.get("llm", {})),
    )


@router.put("/llm", response_model=ApiResponse[LLMSettings])
async def update_llm_settings(data: LLMSettings):
    """更新LLM配置"""
    sm = get_settings_manager()
    sm.update({"llm": data.model_dump()})
    
    # 重置 RAG 服务的配置缓存，使其能重新检测 Embedding 配置状态
    from app.services.rag_service import get_rag_service
    get_rag_service().reset_config_cache()
    
    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="LLM配置更新成功",
        data=LLMSettings(**config.get("llm", {})),
    )


@router.get("/datasource", response_model=ApiResponse[DatasourceSettings])
async def get_datasource_settings():
    """获取数据源配置"""
    sm = get_settings_manager()
    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="success",
        data=DatasourceSettings(**config.get("datasource", {})),
    )


@router.put("/datasource", response_model=ApiResponse[DatasourceSettings])
async def update_datasource_settings(data: DatasourceSettings):
    """更新数据源配置"""
    sm = get_settings_manager()
    sm.update({"datasource": data.model_dump()})
    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="数据源配置更新成功",
        data=DatasourceSettings(**config.get("datasource", {})),
    )


@router.get("/rag", response_model=ApiResponse[RAGSettings])
async def get_rag_settings():
    """获取RAG配置"""
    sm = get_settings_manager()
    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="success",
        data=RAGSettings(**config.get("rag", {})),
    )


@router.put("/rag", response_model=ApiResponse[RAGSettings])
async def update_rag_settings(data: RAGSettings):
    """更新RAG配置"""
    sm = get_settings_manager()
    sm.update({"rag": data.model_dump()})

    # 重置 RAG 服务的配置缓存，使其能重新检测 Embedding 配置状态
    from app.services.rag_service import get_rag_service
    get_rag_service().reset_config_cache()

    config = sm.get_all()
    return ApiResponse(
        code=200,
        message="RAG配置更新成功",
        data=RAGSettings(**config.get("rag", {})),
    )


@router.post("/llm/test", response_model=ApiResponse[LLMTestResponse])
async def test_llm_connection(request: LLMTestRequest):
    """测试LLM连接"""
    sm = get_settings_manager()
    config = sm.get_all()
    llm_config = config.get("llm", {})

    api_base_url = request.api_base_url or llm_config.get("api_base_url", "")
    api_key = request.api_key or llm_config.get("api_key", "")
    model = request.model or llm_config.get("model", "")

    if not api_base_url:
        return ApiResponse(
            code=200,
            message="测试完成",
            data=LLMTestResponse(
                success=False,
                message="未配置 API Base URL，请先在设置中填写",
            ),
        )

    if not api_key:
        return ApiResponse(
            code=200,
            message="测试完成",
            data=LLMTestResponse(
                success=False,
                message="未配置 API Key，请先在设置中填写",
            ),
        )

    if not model:
        return ApiResponse(
            code=200,
            message="测试完成",
            data=LLMTestResponse(
                success=False,
                message="未配置模型名称，请先在设置中填写",
            ),
        )

    try:
        from openai import OpenAI

        start_time = time.time()

        client = OpenAI(api_key=api_key, base_url=api_base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "你好，请回复'连接测试成功'"}],
            max_tokens=20,
        )

        latency = (time.time() - start_time) * 1000

        if response.choices and response.choices[0].message.content:
            return ApiResponse(
                code=200,
                message="测试完成",
                data=LLMTestResponse(
                    success=True,
                    message=f"连接成功：{response.choices[0].message.content}",
                    latency_ms=round(latency, 2),
                ),
            )
        else:
            return ApiResponse(
                code=200,
                message="测试完成",
                data=LLMTestResponse(
                    success=False,
                    message="连接成功但未获得有效响应",
                    latency_ms=round(latency, 2),
                ),
            )

    except Exception as e:
        logger.error(f"LLM连接测试失败: {e}")
        return ApiResponse(
            code=200,
            message="测试完成",
            data=LLMTestResponse(
                success=False,
                message=f"连接失败：{str(e)[:200]}",
            ),
        )
