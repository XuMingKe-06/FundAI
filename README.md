# FundAI Server - 多智能体场外基金分析决策系统后端

## 项目概述

FundAI Server 是多智能体场外基金分析决策系统的后端服务，提供基金分析、决策建议等功能的RESTful API。

## 技术栈

- **Python 3.11+** - 主要开发语言
- **FastAPI 0.109+** - Web框架
- **SQLAlchemy 2.0+** - ORM
- **PostgreSQL 15+** - 主数据库
- **Redis 7.0+** - 缓存和消息队列
- **LangChain/LangGraph** - 智能体框架

## 项目结构

```
FundAI_Server/
├── app/
│   ├── api/                    # API路由
│   │   └── v1/
│   │       └── endpoints/      # API端点
│   │           ├── auth.py     # 认证API
│   │           ├── funds.py    # 基金API
│   │           ├── analysis.py # 分析API
│   │           └── sessions.py # 会话API
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 应用配置
│   │   ├── database.py         # 数据库连接
│   │   ├── redis_client.py     # Redis客户端
│   │   └── security.py         # 安全认证
│   ├── models/                 # 数据库模型
│   │   ├── user.py             # 用户模型
│   │   ├── fund.py             # 基金模型
│   │   ├── analysis.py         # 分析模型
│   │   └── audit.py            # 审计模型
│   ├── schemas/                # Pydantic模型
│   │   ├── common.py           # 通用响应
│   │   ├── auth.py             # 认证Schema
│   │   ├── fund.py             # 基金Schema
│   │   └── analysis.py         # 分析Schema
│   ├── agents/                 # 智能体模块
│   │   ├── base.py             # 智能体基类
│   │   ├── fundamental.py      # 基本面分析师
│   │   ├── technical.py        # 技术分析师
│   │   ├── risk.py             # 风险分析师
│   │   ├── cost.py             # 成本分析师
│   │   ├── sentiment.py        # 情绪分析师
│   │   ├── decision.py         # 决策智能体
│   │   └── orchestrator.py     # 智能体编排器
│   ├── data_sources/           # 数据源适配器
│   ├── services/               # 业务服务
│   └── main.py                 # 应用入口
├── migrations/                 # 数据库迁移
│   └── init_db.py              # 初始化脚本
├── tests/                      # 测试模块
├── requirements.txt            # 依赖列表
├── .env.example                # 环境变量示例
└── README.md                   # 项目说明
```

## 快速开始

### 1. 环境准备

确保已安装以下软件：
- Python 3.11+
- PostgreSQL 15+
- Redis 7.0+

### 2. 安装依赖

```bash
cd FundAI_Server
python -m venv venv
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
copy .env.example .env
# 编辑 .env 文件，配置数据库连接等信息
```

### 4. 初始化数据库

```bash
python -m migrations.init_db
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问API文档

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## API接口

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
| GET | /api/v1/analysis/sessions/{session_id}/stream | SSE流式分析 |
| GET | /api/v1/analysis/sessions/{session_id}/report | 获取分析报告 |

### 会话接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/v1/sessions | 获取会话列表 |
| GET | /api/v1/sessions/{session_id} | 获取会话详情 |

## 测试账号

- 普通用户: 手机号 `13800138000`, 密码 `password123`
- 管理员: 手机号 `13900139000`, 密码 `admin123`

## 开发说明

### 代码规范

- 遵循PEP 8规范
- 使用类型注解
- 添加中文注释

### 数据库迁移

使用Alembic进行数据库迁移管理：

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1
```

## License

MIT
