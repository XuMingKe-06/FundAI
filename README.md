# FundAI - 多智能体场外基金分析决策系统

## 项目概述

FundAI 是一个基于多智能体协作的场外基金分析决策系统，通过多个专业智能体（基本面分析师、技术分析师、风险分析师、成本分析师、情绪分析师）协同工作，为用户提供经过成本校验的投资建议。

## 技术栈

### 后端
- **Python 3.12+** - 主要开发语言
- **FastAPI 0.109+** - Web框架
- **SQLAlchemy 2.0+** - ORM
- **PostgreSQL 15+** - 主数据库
- **Redis 7.0+** - 缓存和消息队列
- **LangChain/LangGraph** - 智能体框架

### 前端
- **Nuxt 4.x** - Vue.js 全栈框架
- **Vue 3.5+** - 前端框架
- **Element Plus** - UI组件库
- **Pinia** - 状态管理
- **ECharts** - 图表库
- **TypeScript** - 类型支持

## 项目结构

```
FundAI/
├── app/                        # 后端应用
│   ├── api/                    # API路由
│   │   └── v1/
│   │       └── endpoints/      # API端点
│   ├── core/                   # 核心配置
│   ├── models/                 # 数据库模型
│   ├── schemas/                # Pydantic模型
│   ├── agents/                 # 智能体模块
│   ├── data_sources/           # 数据源适配器
│   ├── services/               # 业务服务
│   └── main.py                 # 应用入口
├── frontend/                   # 前端应用
│   ├── app/                    # Nuxt应用目录
│   │   ├── components/         # Vue组件
│   │   ├── composables/        # 组合式函数
│   │   ├── pages/              # 页面路由
│   │   ├── services/           # API服务
│   │   ├── stores/             # Pinia状态管理
│   │   └── utils/              # 工具函数
│   ├── public/                 # 静态资源
│   ├── server/                 # Nuxt服务端
│   ├── nuxt.config.ts          # Nuxt配置
│   └── package.json            # 前端依赖
├── database/                   # 数据库脚本
├── tests/                      # 测试模块
├── requirements.txt            # 后端依赖
└── README.md                   # 项目说明
```

## 快速开始

### 1. 环境准备

确保已安装以下软件：
- Python 3.12+
- Node.js 22+
- PostgreSQL 15+
- Redis 7.0+

### 2. 后端设置

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

### 3. 前端设置

```powershell
# 进入前端目录
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

### 4. 访问应用

- 前端应用: http://localhost:3000
- 后端API文档: http://localhost:8000/docs
- 健康检查: http://localhost:8000/health

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

## 开发说明

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

## License

MIT
