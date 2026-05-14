# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FundAI 是一个多智能体场外基金分析决策系统。后端使用 Python FastAPI + PostgreSQL + Redis，前端使用 Nuxt 4 + Vue 3 + Element Plus。通过 5 个分析智能体（基本面、技术、风险、成本、情绪）并行分析，再由决策智能体综合生成投资建议，通过 SSE 流式推送分析过程。

## 开发命令

### 后端
```bash
# 启动开发服务器（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 运行测试
pytest

# 运行单个测试
pytest tests/test_agents/test_technical.py -v

# 代码格式化
black app/
isort app/

# 创建虚拟环境
python -m venv .venv
# Windows: .venv\Scripts\activate
# 安装依赖
pip install -r requirements.txt
```

### 前端
```bash
cd frontend
npm run dev    # 启动开发服务器 (localhost:3000)
npm run build  # 生产构建
npm run preview # 预览生产构建
npm run typecheck # TypeScript 类型检查
```

### 数据库
- 初始化：执行 `database/init_db.sql`
- 配置 `.env` 中的 `DATABASE_URL`

## 架构概览

### 后端分层 (`app/`)

```
app/
├── main.py                 # FastAPI 入口，CORS，异常处理
├── core/                   # 基础设施
│   ├── config.py           # pydantic-settings 配置（支持 .env）
│   ├── database.py         # SQLAlchemy async engine + session
│   ├── redis_client.py     # Redis 缓存客户端
│   └── security.py         # JWT 认证
├── models/                 # SQLAlchemy ORM 模型
│   ├── fund.py             # Fund, FundNav, FundHolding, FundFee
│   ├── user.py             # User, UserSettings（手机号注册 + JWT）
│   └── analysis.py         # AnalysisSession, AgentOutput, DecisionReport
├── schemas/                # Pydantic 响应模型
├── api/v1/endpoints/       # FastAPI 路由
│   ├── auth.py             # 手机验证码登录/注册
│   ├── funds.py            # 基金搜索、详情、净值、持仓、费率
│   ├── analysis.py         # 创建会话、SSE 流式分析、获取报告
│   ├── sessions.py         # 会话列表/详情
│   └── knowledge.py        # 知识库 CRUD
├── agents/                 # 多智能体系统（核心）
│   ├── base.py             # BaseAgent：LLM调用、工具调用、RAG、流式思考
│   ├── orchestrator.py     # AgentOrchestrator：编排5+1智能体，SSE事件推送
│   ├── fundamental.py      # 基本面分析师
│   ├── technical.py        # 技术分析师（内置MA/MACD/RSI计算）
│   ├── risk.py             # 风险分析师（波动率/最大回撤/夏普/Beta）
│   ├── cost.py             # 成本分析师（费率矩阵/短线可行性）
│   ├── sentiment.py        # 情绪分析师
│   ├── decision.py         # 决策智能体（汇总生成双轨建议）
│   ├── prompts/            # 各智能体的 system prompt 模板
│   └── tools/              # ToolRegistry + 具体工具实现
├── data_sources/           # 数据源层
│   ├── manager.py          # DataSourceManager：主备切换 + Redis缓存
│   ├── tushare_adapter.py  # Tushare（主数据源）
│   └── akshare_adapter.py  # AKShare（备份数据源）
└── services/               # 业务服务
    ├── llm_service.py      # LLMService：阿里云百炼 API 封装（同步/流式/工具）
    ├── rag_service.py      # RAGService：向量检索 + 上下文构建
    ├── knowledge_service.py # 文档导入/分块/管理
    ├── vector_store_service.py # ChromaDB 向量存储封装
    └── embedding_service.py    # Embedding 生成
```

### 关键架构设计

**多智能体编排**：`AgentOrchestrator` 协调 5 个分析智能体（并行或串行）+ 1 个决策智能体。执行流程分为两阶段：
1. 分析阶段：所有分析智能体并行运行，通过 `asyncio.gather` 并发执行
2. 决策阶段：汇总分析结果后，由决策智能体生成短线（7-30天）和长线（6个月+）双轨建议

**SSE 流式推送**：分析过程通过 Server-Sent Events 实时推送。设计了重连机制，支持页面刷新后恢复流式分析展示。事件类型包括：`agent_status`、`thinking`、`llm_thinking_stream`、`tool_call`、`agent_complete`、`analysis_complete`、`agent_snapshot`（重连用）。

**数据源层**：`DataSourceManager` 管理主数据源（Tushare）和备用数据源（AKShare），自动故障切换。所有数据通过 Redis 缓存（不同数据类型的过期时间不同）。

**LLM 集成**：通过阿里云百炼 API（兼容 OpenAI SDK）调用。支持流式输出、工具调用（function calling）、深度思考（reasoning_content）。`BaseAgent` 实现最多 5 轮工具调用循环。

### 前端 (`frontend/`)

```
frontend/
├── nuxt.config.ts          # Nuxt 4 配置（Element Plus、ECharts、Pinia）
├── app/
│   ├── pages/              # index.vue（首页），workspace.vue（分析工作台）
│   ├── components/         # AgentView, ReportView, SidebarLeft/Right, Header 等
│   ├── stores/             # Pinia：agent, analysis, auth, session
│   ├── services/           # API 调用封装
│   └── composables/        # 组合式函数
```

### 数据流

1. 用户在前端搜索基金 → 调 `GET /api/v1/funds/search`
2. 发起分析 → `POST /api/v1/analysis/sessions` 创建会话
3. 前端连接 SSE → `GET /api/v1/analysis/sessions/{id}/stream`
4. 后端 `AgentOrchestrator` 执行两阶段分析，通过 SSE 实时推送事件
5. 完成后，agent outputs 和 decision report 持久化到 PostgreSQL
6. 前端通过 `GET /api/v1/analysis/sessions/{id}/report` 获取完整报告

### 数据库表

- **funds**: 基金基础信息（代码、名称、类型、基金经理、费率等）
- **fund_nav**: 净值历史（日期、单位净值、累计净值、日增长率）
- **fund_holdings**: 持仓明细（股票代码、名称、占比等）
- **fund_fees**: 费率阶梯（类型、持有天数范围、费率）
- **users**: 用户（手机号注册）
- **analysis_sessions**: 分析会话（关联用户、基金、状态、分析模式）
- **agent_outputs**: 智能体输出快照（用于重连恢复）
- **decision_reports**: 决策报告（长短线建议、成本矩阵、风险提示、趋势图）

### 测试

```bash
# 组织结构
tests/
├── conftest.py
├── test_integration.py
├── test_orchestrator.py
├── test_agents/        # 各智能体单元测试
├── test_prompts/       # 提示词测试
└── test_tools/         # 工具测试
```

## 重要规范

### Git 提交格式

遵循 Conventional Commits（中文描述）：
```
<类型>(可选范围): <简洁标题>

<详细描述>

<可选脚注>
```
类型：feat / fix / docs / style / refactor / perf / test / chore

### 环境变量

参考 `.env.example`，必须配置：
- `DATABASE_URL`（PostgreSQL 连接串）
- `REDIS_URL`
- `DASHSCOPE_API_KEY` 或 `ALIYUN_LLM_API_KEY`（阿里云百炼）
- `JWT_SECRET_KEY`（生产环境需修改）
