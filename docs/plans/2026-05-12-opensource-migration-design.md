# FundAI 开源化改造设计文档

**目标：** 将 FundAI 从公开网站架构改造为开源本地应用架构，允许任何人安装在本地使用。

**架构变更：** PostgreSQL -> SQLite | Redis -> 文件缓存 | 删除用户认证系统 | 新增前端配置界面

**技术栈：** Python 3.12 + FastAPI + SQLite + aiosqlite + cachetools + Nuxt 4 + Vue 3

***

## 一、需求概述

### 1.1 变更背景

项目原先预计以公开网站的形式上线，现在计划变更为开源项目发布在 GitHub 上，允许任何人安装在本地使用。

### 1.2 核心变更点

| 变更项  | 原方案         | 新方案               |
| ---- | ----------- | ----------------- |
| 数据库  | PostgreSQL  | SQLite            |
| 缓存   | Redis       | 文件缓存              |
| 用户认证 | 手机号+验证码+JWT | 完全移除              |
| 会话管理 | 关联用户        | 本地数据库存储           |
| 审计日志 | 关联用户        | 完全删除              |
| 配置方式 | 环境变量/.env   | JSON配置文件 + 前端配置界面 |
| 启动方式 | 分别启动前后端     | 一键启动脚本            |
| 部署方式 | 服务器部署       | 源码安装 + Docker     |

### 1.3 保留内容

* 数据源：Tushare + AKShare（用户自行配置 Tushare Token）

* 向量数据库：ChromaDB（数据存储在本地 data/chroma 目录）

* 多智能体分析系统：完整保留

* SSE 流式推送：完整保留

***

## 二、开发阶段规划

### 阶段一：后端核心改造（基础设施层）

**目标：** 完成数据库、缓存、认证系统的改造

**主要任务：**

1. PostgreSQL -> SQLite 迁移
2. Redis -> 文件缓存迁移
3. 删除用户认证系统
4. 删除审计日志模块
5. 修改会话管理逻辑

### 阶段二：后端 API 改造（接口层）

**目标：** 修改所有受影响的 API 端点

**主要任务：**

1. 移除所有 API 的认证依赖
2. 修改会话相关 API
3. 新增配置管理 API
4. 更新 API 文档

### 阶段三：前端改造（用户界面层）

**目标：** 移除认证相关 UI，新增配置界面

**主要任务：**

1. 删除登录/注册相关代码
2. 修改 API 服务层（移除 token 逻辑）
3. 开发独立设置页面
4. 修改工作台页面

### 阶段四：部署与文档（发布层）

**目标：** 提供完整的安装和部署方案

**主要任务：**

1. 编写一键启动脚本
2. 编写 Docker 配置
3. 更新项目文档
4. 更新依赖文件

***

## 三、详细设计

### 3.1 阶段一：后端核心改造

#### 3.1.1 数据库迁移（PostgreSQL -> SQLite）

**涉及文件：**

* `app/core/database.py` - 数据库连接配置

* `app/core/config.py` - 数据库 URL 配置

* `app/models/*.py` - 所有模型文件（UUID、JSONB 类型）

* `.env.example` - 配置示例

**技术方案：**

* 使用 `aiosqlite` 作为异步 SQLite 驱动

* UUID 类型：SQLite 不支持原生 UUID，使用 `String(36)` 存储

* JSONB 类型：SQLite 使用 `JSON` 或 `Text` 存储

* 自增主键：SQLite 使用 `INTEGER PRIMARY KEY AUTOINCREMENT`

**数据库文件位置：** `data/fundai.db`

**模型变更详情：**

| 模型              | 变更内容                              |
| --------------- | --------------------------------- |
| User            | 删除整个模型                            |
| UserSettings    | 删除整个模型                            |
| AuditLog        | 删除整个模型                            |
| SystemMetric    | 删除整个模型                            |
| AnalysisSession | 移除 `user_id` 外键约束                 |
| Fund            | 保持不变                              |
| FundNav         | 保持不变                              |
| FundHolding     | 保持不变                              |
| FundFee         | 保持不变                              |
| AgentOutput     | UUID -> String(36)                |
| DecisionReport  | UUID -> String(36), JSONB -> JSON |

#### 3.1.2 缓存迁移（Redis -> 文件缓存）

**涉及文件：**

* `app/core/redis_client.py` - 重写为文件缓存模块

* `app/core/config.py` - 缓存配置

* 所有使用 Redis 的文件

**技术方案：**

* 使用 `diskcache` 库实现文件缓存

* 缓存文件位置：`data/cache/`

* 支持过期时间设置

* 线程安全

**缓存键映射：**

| 原 Redis 键                                    | 新文件缓存键                                       |
| -------------------------------------------- | -------------------------------------------- |
| `fund:info:{fund_code}`                      | `fund_info_{fund_code}`                      |
| `fund:nav:{fund_code}:{date}`                | `fund_nav_{fund_code}_{date}`                |
| `fund:nav_history:{fund_code}:{start}:{end}` | `fund_nav_history_{fund_code}_{start}_{end}` |
| `fund:holdings:{fund_code}:{report_date}`    | `fund_holdings_{fund_code}_{report_date}`    |
| `fund:fees:{fund_code}`                      | `fund_fees_{fund_code}`                      |
| `analysis:result:{session_id}`               | `analysis_result_{session_id}`               |
| `agent:status:{session_id}:{agent_type}`     | `agent_status_{session_id}_{agent_type}`     |
| `datasource:health:{source_name}`            | `datasource_health_{source_name}`            |

**删除的缓存键：**

* `session:{session_id}` - 用户会话缓存

* `user:preference:{user_id}` - 用户偏好缓存

* `verify:code:{phone}:{type}` - 验证码缓存

* `jwt:blacklist:{token_jti}` - JWT 黑名单

* `ratelimit:{user_id}:{endpoint}` - 限流键

#### 3.1.3 删除用户认证系统

**删除的文件：**

* `app/core/security.py` - JWT 认证模块

* `app/api/v1/endpoints/auth.py` - 认证 API

* `app/schemas/auth.py` - 认证相关 Schema

* `app/models/user.py` - 用户模型

* `app/models/audit.py` - 审计日志模型

**修改的文件：**

* `app/models/analysis.py` - 移除 `user_id` 外键

* `app/models/__init__.py` - 移除用户模型导入

* `app/api/__init__.py` - 移除认证路由

* `app/main.py` - 移除 Redis 关闭逻辑

#### 3.1.4 会话管理改造

**AnalysisSession 模型变更：**

```python
# 移除字段
user_id = Column(UUID, ForeignKey("users.id"))  # 删除

# 保留字段
id = Column(String(36), primary_key=True)  # UUID -> String
fund_code = Column(String(6), ForeignKey("funds.fund_code"))
user_preference = Column(String(20), default="neutral")
analysis_mode = Column(String(20), default="parallel")
previous_session_id = Column(String(36), ForeignKey("analysis_sessions.id"))
status = Column(String(20), default="pending")
created_at = Column(DateTime, default=datetime.utcnow)
completed_at = Column(DateTime, nullable=True)
```

***

### 3.2 阶段二：后端 API 改造

#### 3.2.1 移除认证依赖

**涉及文件：**

* `app/api/v1/endpoints/analysis.py`

* `app/api/v1/endpoints/sessions.py`

* `app/api/v1/endpoints/knowledge.py`

**变更内容：**

* 移除所有 `Depends(get_current_user)` 依赖

* 移除所有 `Depends(get_current_user_from_query_or_header)` 依赖

* 移除用户权限验证逻辑

#### 3.2.2 会话 API 改造

**GET /api/v1/sessions**

* 移除用户过滤条件

* 返回所有会话列表

**DELETE /api/v1/sessions/{session\_id}**

* 移除用户权限验证

**GET /api/v1/sessions/{session\_id}**

* 移除用户权限验证

**POST /api/v1/analysis/sessions**

* 移除 `user_id` 字段设置

**GET /api/v1/analysis/sessions/{session\_id}/stream**

* 移除用户权限验证

**GET /api/v1/analysis/sessions/{session\_id}/report**

* 移除用户权限验证

#### 3.2.3 新增配置管理 API

**新建文件：** `app/api/v1/endpoints/settings.py`

**API 设计：**

| 方法   | 路径                          | 描述        |
| ---- | --------------------------- | --------- |
| GET  | /api/v1/settings            | 获取所有配置    |
| PUT  | /api/v1/settings            | 更新配置      |
| GET  | /api/v1/settings/llm        | 获取 LLM 配置 |
| PUT  | /api/v1/settings/llm        | 更新 LLM 配置 |
| GET  | /api/v1/settings/datasource | 获取数据源配置   |
| PUT  | /api/v1/settings/datasource | 更新数据源配置   |
| POST | /api/v1/settings/llm/test   | 测试 LLM 连接 |

**配置文件结构：** `data/config.json`

```json
{
  "llm": {
    "provider": "aliyun",
    "api_key": "sk-xxx",
    "model": "qwen3-vl-235b-a22b-thinking",
    "embedding_model": "text-embedding-v3"
  },
  "datasource": {
    "tushare_token": "xxx"
  },
  "rag": {
    "embedding_mode": "aliyun",
    "top_k": 5,
    "chunk_size": 500,
    "chunk_overlap": 50
  }
}
```

***

### 3.3 阶段三：前端改造

#### 3.3.1 删除认证相关代码

**删除的文件：**

* `frontend/app/stores/auth.ts` - 认证状态管理

* `frontend/app/services/auth.ts` - 认证服务

**修改的文件：**

* `frontend/app/services/api.ts` - 移除 token 注入逻辑

* `frontend/app/pages/index.vue` - 移除登录弹窗、用户菜单

* `frontend/app/pages/workspace.vue` - 移除认证检查

#### 3.3.2 API 服务层改造

**frontend/app/services/api.ts 变更：**

* 移除请求拦截器中的 token 注入

* 移除响应拦截器中的 token 刷新逻辑

* 移除 401 错误处理中的登录跳转

#### 3.3.3 首页改造

**frontend/app/pages/index.vue 变更：**

* 移除登录弹窗组件

* 移除用户菜单组件

* 移除登录状态检查

* 移除 `pendingFundCode` 逻辑

* 直接跳转到工作台，无需登录验证

#### 3.3.4 新增设置页面

**新建文件：** `frontend/app/pages/settings.vue`

**页面结构：**

```
设置页面
├── LLM 配置
│   ├── 服务商选择（阿里云百炼 / OpenAI / 本地模型）
│   ├── API Key 输入
│   ├── 模型选择
│   ├── Embedding 模型选择
│   └── 连接测试按钮
├── 数据源配置
│   ├── Tushare Token 输入
│   └── 数据源状态显示
├── RAG 配置
│   ├── Embedding 模式选择
│   ├── Top K 设置
│   ├── Chunk Size 设置
│   └── Chunk Overlap 设置
└── 关于
    ├── 版本信息
    └── GitHub 链接
```

**导航入口：**

* 工作台顶部导航栏添加"设置"按钮

* 首页导航栏添加"设置"按钮

***

### 3.4 阶段四：部署与文档

#### 3.4.1 一键启动脚本

**Windows:** **`start.bat`**

```batch
@echo off
echo Starting FundAI...
start /b cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
start /b cmd /c "cd frontend && npm run dev"
echo FundAI is running!
echo Backend: http://localhost:8000
echo Frontend: http://localhost:3000
pause
```

**Linux/macOS:** **`start.sh`**

```bash
#!/bin/bash
echo "Starting FundAI..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
cd frontend && npm run dev &
echo "FundAI is running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"
```

#### 3.4.2 Docker 配置

**docker-compose.yml**

```yaml
version: '3.8'
services:
  fundai:
    build: .
    ports:
      - "3000:3000"
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - PYTHONUNBUFFERED=1
```

**Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

# Install Node.js
RUN apt-get update && apt-get install -y nodejs npm

# Install Python dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install frontend dependencies
COPY frontend/package*.json ./frontend/
RUN cd frontend && npm install

# Copy application code
COPY . .

# Build frontend
RUN cd frontend && npm run build

# Expose ports
EXPOSE 8000 3000

# Start command
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port 8000 & cd frontend && npm run dev"]
```

#### 3.4.3 依赖更新

**requirements.txt 变更：**

```
# 移除
asyncpg  # PostgreSQL 异步驱动
psycopg2-binary  # PostgreSQL 同步驱动
redis  # Redis 客户端
bcrypt  # 密码哈希
python-jose  # JWT 处理
passlib  # 密码处理

# 新增
aiosqlite  # SQLite 异步驱动
diskcache  # 文件缓存
```

**frontend/package.json 变更：**

* 无需变更

#### 3.4.4 文档更新

**更新 CLAUDE.md：**

* 更新数据库配置说明

* 更新缓存配置说明

* 移除认证相关说明

* 添加配置管理说明

**新建 README.md：**

* 项目介绍

* 功能特点

* 安装指南（源码安装 + Docker）

* 配置指南

* 使用指南

* 开发指南

* 常见问题

**新建 docs/installation.md：**

* 环境要求

* 源码安装步骤

* Docker 安装步骤

* 配置步骤

***

## 四、文件变更清单

### 4.1 删除的文件

| 文件路径                            | 原因        |
| ------------------------------- | --------- |
| `app/core/security.py`          | JWT 认证模块  |
| `app/core/redis_client.py`      | Redis 客户端 |
| `app/api/v1/endpoints/auth.py`  | 认证 API    |
| `app/schemas/auth.py`           | 认证 Schema |
| `app/models/user.py`            | 用户模型      |
| `app/models/audit.py`           | 审计日志模型    |
| `frontend/app/stores/auth.ts`   | 前端认证状态    |
| `frontend/app/services/auth.ts` | 前端认证服务    |

### 4.2 新建的文件

| 文件路径                                             | 用途                |
| ------------------------------------------------ | ----------------- |
| `app/core/cache.py`                              | 文件缓存模块            |
| `app/core/settings_manager.py`                   | 配置管理模块            |
| `app/api/v1/endpoints/settings.py`               | 配置 API            |
| `app/schemas/settings.py`                        | 配置 Schema         |
| `frontend/app/pages/settings.vue`                | 设置页面              |
| `frontend/app/components/SettingsLLM.vue`        | LLM 配置组件          |
| `frontend/app/components/SettingsDatasource.vue` | 数据源配置组件           |
| `frontend/app/components/SettingsRAG.vue`        | RAG 配置组件          |
| `start.bat`                                      | Windows 启动脚本      |
| `start.sh`                                       | Linux/macOS 启动脚本  |
| `docker-compose.yml`                             | Docker Compose 配置 |
| `Dockerfile`                                     | Docker 镜像配置       |
| `data/.gitkeep`                                  | 数据目录占位            |
| `data/cache/.gitkeep`                            | 缓存目录占位            |
| `data/config.json`                               | 默认配置文件            |

### 4.3 修改的文件

| 文件路径                                | 变更内容                       |
| ----------------------------------- | -------------------------- |
| `app/core/database.py`              | PostgreSQL -> SQLite       |
| `app/core/config.py`                | 移除 Redis/JWT/短信配置，简化配置     |
| `app/models/analysis.py`            | 移除 user\_id，UUID -> String |
| `app/models/fund.py`                | UUID -> String             |
| `app/models/__init__.py`            | 移除用户模型导入                   |
| `app/api/__init__.py`               | 移除认证路由，添加设置路由              |
| `app/api/v1/endpoints/analysis.py`  | 移除认证依赖                     |
| `app/api/v1/endpoints/sessions.py`  | 移除认证依赖                     |
| `app/api/v1/endpoints/knowledge.py` | 移除认证依赖                     |
| `app/main.py`                       | 移除 Redis 关闭逻辑              |
| `app/data_sources/manager.py`       | Redis -> 文件缓存              |
| `app/agents/orchestrator.py`        | Redis -> 文件缓存              |
| `frontend/app/services/api.ts`      | 移除 token 逻辑                |
| `frontend/app/pages/index.vue`      | 移除登录相关 UI                  |
| `frontend/app/pages/workspace.vue`  | 移除认证检查                     |
| `requirements.txt`                  | 更新依赖                       |
| `.env.example`                      | 简化配置                       |
| `CLAUDE.md`                         | 更新文档                       |

***

## 五、数据目录结构

```
data/
├── fundai.db           # SQLite 数据库文件
├── cache/              # 文件缓存目录
│   ├── fund_info_*
│   ├── fund_nav_*
│   └── ...
├── chroma/             # ChromaDB 向量数据库
│   └── ...
└── config.json         # 用户配置文件
```

***

## 六、风险与注意事项

### 6.1 数据迁移

* 现有 PostgreSQL 数据无法直接迁移到 SQLite

* 建议提供数据导出工具（如有需要）

### 6.2 性能考虑

* SQLite 单文件数据库在高并发场景下性能可能不如 PostgreSQL

* 文件缓存性能可能不如 Redis

* 对于本地单用户场景，性能影响可接受

### 6.3 安全考虑

* API Key 存储在本地 JSON 文件中，需提醒用户注意保护

* 建议在 .gitignore 中添加 `data/config.json`

### 6.4 兼容性

* SQLite 不支持某些 PostgreSQL 特有功能（如 JSONB 操作符）

* 需要检查所有 SQL 查询的兼容性

***

## 七、测试计划

### 7.1 单元测试

* 文件缓存模块测试

* 配置管理模块测试

* SQLite 数据库操作测试

### 7.2 集成测试

* API 端点测试（无认证）

* SSE 流式推送测试

* 配置保存与读取测试

### 7.3 端到端测试

* 完整分析流程测试

* 设置页面配置测试

* 启动脚本测试

***

## 八、时间估算

| 阶段            | 预计工作量      |
| ------------- | ---------- |
| 阶段一：后端核心改造    | 2-3 天      |
| 阶段二：后端 API 改造 | 1-2 天      |
| 阶段三：前端改造      | 2-3 天      |
| 阶段四：部署与文档     | 1-2 天      |
| **总计**        | **6-10 天** |

***

## 九、后续扩展

### 9.1 桌面端应用

* 使用 Electron 或 Tauri 打包为桌面应用

* 复用现有前端代码

* 后端服务内嵌或独立运行

### 9.2 多语言支持

* 添加 i18n 国际化支持

* 支持中文/英文切换

### 9.3 数据导入导出

* 支持会话数据导出

* 支持配置导入导出

