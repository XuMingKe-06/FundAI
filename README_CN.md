<div align="center">

# FundAI - 多智能体场外基金分析决策系统

</div>

> 本项目目前处于早期开发阶段。功能、API 和文档可能会频繁变更。目前不建议在生产环境中使用。欢迎贡献代码和反馈！

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node.js-22+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5+-4FC08D.svg)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg)](https://redis.io/)
[![许可证](https://img.shields.io/badge/许可证-MIT-yellow.svg)](LICENSE)

**中文** | **[English](README.md)**

</div>

---

## 项目概述

FundAI 是一个基于多智能体协作的场外基金分析决策系统。通过多个专业智能体（基本面分析师、技术分析师、风险分析师、成本分析师、情绪分析师）协同工作，为用户提供经过成本校验的投资建议。

## 核心特性

- **多智能体协作**：五个专业分析智能体并行/串行执行
- **智能决策**：决策智能体汇总所有分析结果，给出短线/长线投资建议
- **实时流式推送**：基于 SSE 的分析过程实时可视化
- **辩论机制**：检测评分分歧，触发智能体辩论并调整评分
- **RAG 知识增强**：LLM 驱动的智能体具备工具调用和 RAG 知识增强能力
- **数据质量验证**：内置数据质量验证和来源追踪机制
- **灵活数据源**：支持 AKShare 和 Tushare Pro 数据源，自动切换和缓存

## 技术架构

### 后端技术栈

| 组件 | 技术 |
|------|------|
| **运行时** | Python 3.12+ |
| **框架** | FastAPI 0.109+ |
| **ORM** | SQLAlchemy 2.0+ (异步) |
| **数据库** | PostgreSQL 15+ |
| **缓存** | Redis 7.0+ |
| **智能体框架** | LangChain / LangGraph |
| **向量存储** | ChromaDB |
| **数据源** | AKShare, Tushare Pro |

### 前端技术栈

| 组件 | 技术 |
|------|------|
| **框架** | Nuxt 4.x |
| **UI** | Vue 3.5+ |
| **UI 组件** | Element Plus |
| **状态管理** | Pinia |
| **图表** | ECharts |
| **语言** | TypeScript |

## 项目结构

```
FundAI/
├── app/                        # 后端应用
│   ├── api/v1/endpoints/       # API 端点
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 设置管理
│   │   ├── database.py         # 异步数据库引擎
│   │   ├── cache.py            # Redis 缓存
│   │   └── calculations/       # 技术指标计算
│   ├── models/                 # SQLAlchemy ORM 模型
│   ├── schemas/                # Pydantic 模型
│   ├── agents/                 # 多智能体系统
│   │   ├── base.py             # BaseAgent 实现
│   │   ├── orchestrator.py     # 智能体编排
│   │   ├── fundamental.py      # 基本面分析师
│   │   ├── technical.py       # 技术分析师
│   │   ├── risk.py             # 风险分析师
│   │   ├── cost.py             # 成本分析师
│   │   ├── sentiment.py       # 情绪分析师
│   │   ├── decision.py         # 决策分析师
│   │   ├── prompts/            # 系统提示词
│   │   └── tools/              # 智能体工具
│   ├── data_sources/           # 数据源适配器
│   ├── services/               # 业务服务
│   └── main.py                 # 应用入口
├── frontend/                   # 前端应用
│   ├── app/                    # Nuxt 应用目录
│   │   ├── components/         # Vue 组件
│   │   ├── composables/        # 组合式函数
│   │   ├── pages/              # 页面路由
│   │   ├── services/           # API 服务
│   │   ├── stores/             # Pinia 状态管理
│   │   └── utils/              # 工具函数
│   ├── server/                 # Nuxt 服务端
│   └── nuxt.config.ts          # Nuxt 配置
├── database/                   # 数据库脚本
├── tests/                      # 测试模块
├── requirements.txt            # 后端依赖
└── README.md                   # 项目文档
```

## 快速开始

### 环境准备

确保已安装以下软件：
- Python 3.12+
- Node.js 22+
- PostgreSQL 15+
- Redis 7.0+

### 后端设置

```powershell
# 创建虚拟环境
python -m venv venv
.\venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
copy .env.example .env
# 编辑 .env 文件，配置数据库连接等信息

# 初始化数据库
# 执行 database/init_db.sql

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 前端设置

```powershell
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 访问应用

- 前端应用: http://localhost:3000
- 后端 API 文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

## API 接口

### 认证接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/auth/send-code | 发送验证码 |
| POST | /api/v1/auth/register | 用户注册 |
| POST | /api/v1/auth/login | 用户登录 |
| POST | /api/v1/auth/logout | 用户登出 |
| POST | /api/v1/auth/refresh | 刷新令牌 |

### 基金接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/funds/search | 搜索基金 |
| GET | /api/v1/funds/{fund_code} | 获取基金详情 |
| GET | /api/v1/funds/{fund_code}/nav | 获取净值历史 |
| GET | /api/v1/funds/{fund_code}/holdings | 获取持仓信息 |
| GET | /api/v1/funds/{fund_code}/fees | 获取费率信息 |

### 分析接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/analysis/sessions | 创建分析会话 |
| GET | /api/v1/analysis/sessions/{session_id}/stream | SSE 流式分析 |
| GET | /api/v1/analysis/sessions/{session_id}/report | 获取分析报告 |

### 会话接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/sessions | 获取会话列表 |
| GET | /api/v1/sessions/{session_id} | 获取会话详情 |

## 开发指南

### 后端开发

```powershell
# 运行测试
pytest

# 代码格式化
black app/
isort app/
```

### 前端开发

```powershell
cd frontend

# 构建生产版本
npm run build

# 预览生产版本
npm run preview

# 类型检查
npm run typecheck
```

## Docker 部署

```powershell
# 启动 PostgreSQL + Redis + 应用
docker-compose up -d
```

## 核心架构要点

### 多智能体系统

- **5 个分析智能体**并行/串行执行：基本面、技术面、风险、成本、情绪
- **1 个决策智能体**汇总所有分析结果，给出短线/长线投资建议
- 每个智能体由 LLM 驱动，具备工具调用和 RAG 知识增强能力
- 智能体通过 `EventCallback` 推送 SSE 事件到前端

### 分析流程

1. 构建上下文（获取基金数据 → 数据质量验证 → 数据来源标注）
2. 并行执行 5 个分析智能体
3. **辩论机制**：检测评分分歧（阈值 1.5），分歧双方互相审视并调分
4. 决策智能体汇总评分并生成投资建议
5. 历史结果存入 `AgentMemory`，下次分析时作为参考

### SSE 流式推送

- 使用 `EventCallback` + `asyncio.Queue` 实现实时事件推送
- 事件类型：智能体状态变更、思考过程、工具调用、深度推理、辩论轮次、渐进式更新
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

## 测试策略

- **框架**：pytest + pytest-asyncio（asyncio_mode = auto）
- **数据库**：内存 SQLite 测试数据库，每测试用例自动建表/清表
- **HTTP 客户端**：httpx.AsyncClient + ASGITransport 直接调用 ASGI 应用（不启动真实服务器）
- **关键 Mock Fixtures**：mock_llm_service, mock_datasource_manager, mock_rag_service
- **测试目录组织**：tests/ 按模块组织（test_agents/, test_api/, test_core/ 等）

## 许可证

MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。