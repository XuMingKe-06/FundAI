# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

FundAI - 多智能体场外基金分析决策系统。后端基于 FastAPI + LangChain/LangGraph 构建多智能体协作系统，前端基于 Nuxt 4 + Vue 3 + Element Plus。

## 常用命令

### 后端
```bash
# 启动后端开发服务器
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 安装依赖
pip install -r requirements.txt

# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_api.py -v

# 运行单个测试函数
pytest tests/test_api.py::test_function_name -v

# 代码格式化
black app/ --line-length=88
isort app/ --profile=black

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate   # Windows
```

### 前端
```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器 (默认端口3000)
npm run dev

# 构建生产版本
npm run build

# 预览构建结果
npm run preview

# 类型检查
npm run typecheck
```

### Docker
```bash
# 启动 PostgreSQL + Redis + 应用
docker-compose up -d
```

## 项目架构

### 后端分层 (app/)

```
app/
├── main.py                    # FastAPI 入口，生命周期管理，全局异常处理
├── core/                      # 核心基础设施
│   ├── config.py              # pydantic-settings 配置 (.env → Settings)
│   ├── database.py            # SQLAlchemy async engine + session
│   ├── cache.py               # Redis 缓存
│   ├── calculations/          # 技术指标计算（MA, MACD, RSI, Bollinger, KDJ 等）
│   ├── data_quality.py        # 数据质量验证
│   ├── data_provenance.py     # 数据来源标注
│   └── settings_manager.py    # 前端可配置的 LLM 设置管理 (data/config.json)
├── api/v1/endpoints/          # API 路由
│   ├── funds.py               # 基金搜索/详情/净值/持仓/费率
│   ├── analysis.py            # 创建分析会话 + SSE 流式分析
│   ├── sessions.py            # 会话列表/详情
│   ├── knowledge.py           # RAG 知识库管理
│   └── settings.py            # LLM 设置 CRUD
├── models/                    # SQLAlchemy ORM 模型 (fund.py, analysis.py)
├── schemas/                   # Pydantic 请求/响应模型
├── agents/                    # 多智能体系统（核心业务逻辑）
│   ├── base.py                # BaseAgent: LLM调用、工具执行、RAG检索、输出解析
│   ├── orchestrator.py        # AgentOrchestrator: 智能体编排/调度/辩论/SSE事件
│   ├── fundamental.py         # 基本面分析师
│   ├── technical.py           # 技术分析师
│   ├── risk.py                # 风险分析师
│   ├── cost.py                # 成本分析师
│   ├── sentiment.py           # 情绪分析师
│   ├── decision.py            # 决策分析师（汇总评分并给出投资建议）
│   ├── prompts/               # 各智能体的系统提示词模板
│   └── tools/                 # 智能体工具集（fund_data, market_data, technical_indicators 等）
├── data_sources/              # 数据源适配器
│   ├── base.py                # 抽象基类
│   ├── akshare_adapter.py     # AKShare 数据源
│   ├── tushare_adapter.py     # Tushare Pro 数据源
│   └── manager.py             # DataSourceManager: 多数据源统一管理
├── services/                  # 业务服务
│   ├── llm_service.py         # LLM 调用封装（支持流式 + 工具调用）
│   ├── rag_service.py         # RAG 检索增强生成服务
│   ├── embedding_service.py   # Embedding 服务
│   ├── vector_store_service.py # ChromaDB 向量存储
│   ├── knowledge_service.py   # 知识库管理服务
│   ├── report_service.py      # 分析报告生成服务
│   └── sse_service.py         # SSE 事件推送服务
```

### 前端分层 (frontend/app/)

```
frontend/app/
├── app.vue                    # 根组件
├── pages/                     # 页面路由
│   ├── index.vue              # 首页/基金搜索
│   ├── workspace.vue          # 工作台（核心分析页面）
│   └── settings.vue           # 设置页面
├── components/                # Vue 组件
│   ├── workspace/             # 工作台子组件
│   │   ├── Header.vue         # 顶部导航
│   │   ├── SidebarLeft.vue    # 左侧边栏（会话列表）
│   │   ├── SidebarRight.vue   # 右侧边栏（分析概览）
│   │   ├── TabBar.vue         # 标签页切换
│   │   ├── AgentSwimLane.vue  # 智能体泳道图
│   │   ├── AgentView.vue      # 单个智能体视图
│   │   ├── ReportView.vue     # 分析报告
│   │   ├── ReportExport.vue   # 报告导出
│   │   ├── QuickOverview.vue  # 快速概览
│   │   ├── ExecutiveSummary.vue # 执行摘要
│   │   ├── FundCompareView.vue # 基金对比
│   │   ├── HoldingsTable.vue  # 持仓表格
│   │   ├── NavHistoryTable.vue # 净值历史表格
│   │   ├── ToolCallVisualization.vue # 工具调用可视化
│   │   ├── DataProvenance.vue # 数据来源标注
│   │   └── SettingsDialog.vue # 设置弹窗
│   ├── common/                # 通用组件
│   │   ├── MetricCard.vue     # 指标卡片
│   │   ├── DataTable.vue      # 数据表格
│   │   ├── DataTag.vue        # 数据标签
│   │   ├── RiskLevel.vue      # 风险等级
│   │   ├── StatusBadge.vue    # 状态徽章
│   │   └── TrendArrow.vue     # 趋势箭头
│   ├── RiskSelect.vue         # 风险偏好选择器
│   └── ThinkingIndicator.vue  # 思考指示器
├── stores/                    # Pinia 状态管理
│   ├── analysis.ts            # 分析报告状态（SSE订阅/暂停/恢复）
│   ├── session.ts             # 会话列表状态
│   ├── settings.ts            # 设置状态
│   └── agent.ts               # 智能体状态
├── composables/               # Vue 组合式函数
│   ├── useSSE.ts              # SSE 连接封装
│   ├── useWorkspaceSSE.ts     # 工作台 SSE 处理
│   ├── useWorkspaceAnalysis.ts # 工作台分析逻辑
│   ├── useWorkspaceCharts.ts  # ECharts 图表集成
│   ├── useEcharts.ts          # ECharts 通用封装
│   ├── useAreaChart.ts        # 面积图
│   ├── useGaugeChart.ts       # 仪表盘图
│   ├── useHeatmapChart.ts     # 热力图
│   ├── usePercentileChart.ts  # 百分位图
│   ├── useSunburstChart.ts    # 旭日图
│   ├── useTheme.ts            # 主题管理
│   └── useScrollSnap.ts       # 滚动对齐
├── services/                  # API 服务层
│   ├── api.ts                 # Axios 封装 + 拦截器
│   ├── analysis.service.ts    # 分析 API + 数据映射
│   ├── session.service.ts     # 会话 API
│   ├── settings.ts            # 设置 API
│   └── fund.ts                # 基金数据 API
└── utils/
    ├── format.ts              # 格式化工具（数字/日期/百分比）
    ├── markdown.ts            # Markdown 渲染
    └── toolNameMap.ts         # 工具名称中文化映射
```

## 核心架构要点

### 多智能体系统
- **5 个分析智能体**并行/串行执行：基本面、技术面、风险、成本、情绪
- **1 个决策智能体**汇总所有分析结果，给出短线/长线投资建议
- 每个智能体由 LLM 驱动，具备工具调用和 RAG 知识增强能力
- 智能体通过 `EventCallback` 推送 SSE 事件到前端（`agent_status`, `thinking`, `tool_call`, `agent_complete` 等）

### 分析流程
1. 构建上下文（获取基金数据 → 数据质量验证 → 数据来源标注）
2. 并行执行 5 个分析智能体
3. **辩论机制**：检测评分分歧（阈值 1.5），分歧双方互相审视并调分
4. 决策智能体汇总评分并生成投资建议
5. 历史结果存入 `AgentMemory`，下次分析时作为参考

### SSE 流式推送
- 使用 `EventCallback` + `asyncio.Queue` 实现实时事件推送
- 事件类型包括：智能体状态变更、思考过程、工具调用、深度推理、辩论轮次、渐进式更新
- 前端通过 `EventSource` 订阅，支持暂停/恢复

### API 代理
- 前端 Nuxt 通过 `server/routes/api/v1/[...].ts` 将所有 `/api/v1/*` 请求代理到后端
- 前端使用 `process.env.NUXT_API_URL` 或默认 `http://localhost:8000`

### LLM 配置
- LLM 设置通过前端设置页面管理，存储在 `data/config.json`
- 支持任意 OpenAI 兼容 API（API URL、API Key、模型名称、temperature 等）
- 配置热生效，无需重启服务

### 数据源
- 支持 AKShare 和 Tushare Pro 两种数据源
- `DataSourceManager` 统一管理，支持自动切换和缓存

### 测试策略
- `pytest` + `pytest-asyncio`（`asyncio_mode = auto`）
- 内存 SQLite 测试数据库，每测试用例自动建表/清表
- `httpx.AsyncClient` + `ASGITransport` 直接调用 ASGI 应用（不启动真实服务器）
- 关键 mock fixtures：`mock_llm_service`, `mock_datasource_manager`, `mock_rag_service`
- 测试目录按模块组织：`tests/test_agents/`, `tests/test_api/`, `tests/test_core/`, `tests/test_data_sources/`, `tests/test_services/`, `tests/test_tools/`, `tests/test_prompts/`

### 关键设计决策
- **PostgreSQL 作为数据库**，asyncpg 异步驱动，支持连接池
- **SQLAlchemy async** 全异步数据库操作
- **Redis 作为缓存**，redis.asyncio 异步客户端，支持 TTL 和模式匹配
- **前端通过设置页面管理 LLM 配置**，而非通过 `.env` 文件
- **Nitro 代理**方案而非传统跨域请求，避免 CORS 复杂配置
- **数据来源标注**机制追踪每条数据的来源和获取时间
