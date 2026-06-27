<div align="center">

# FundAI - Multi-Agent Fund Analysis & Decision System

</div>

> This project is currently in the early development stage. Features, APIs. Production use is not recommended at this time. Contributions and feedback are welcome!

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![Node](https://img.shields.io/badge/Node.js-22+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-009688.svg)](https://fastapi.tiangolo.com/)
[![Vue](https://img.shields.io/badge/Vue-3.5+-4FC08D.svg)](https://vuejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.0+-DC382D.svg)](https://redis.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**[中文](README_CN.md)** | **English**

</div>

---

## Overview

FundAI is a multi-agent collaborative fund analysis and decision-making system. Through coordinated work of multiple specialized agents (Fundamental Analyst, Technical Analyst, Risk Analyst, Cost Analyst, and Sentiment Analyst), it provides users with investment recommendations that have undergone cost verification.

## Key Features

- **Multi-Agent Collaboration**: Five specialized analytical agents working in parallel/series
- **Intelligent Decision Making**: Decision agent synthesizes all analysis results to provide short-term/long-term investment recommendations
- **Real-time Streaming**: SSE-based streaming analysis process visualization
- **Debate Mechanism**: Detects scoring divergence and triggers agent debates for adjustment
- **RAG Knowledge Enhancement**: LLM-driven agents with tool invocation and RAG knowledge enhancement
- **Data Quality Validation**: Built-in data quality verification and provenance tracking
- **Flexible Data Sources**: Support for AKShare and Tushare Pro data sources with auto-switching and caching

## Architecture

### Backend

| Component | Technology |
|-----------|------------|
| **Runtime** | Python 3.12+ |
| **Framework** | FastAPI 0.109+ |
| **ORM** | SQLAlchemy 2.0+ (Async) |
| **Database** | PostgreSQL 15+ |
| **Cache** | Redis 7.0+ |
| **Agent Framework** | LangChain / LangGraph |
| **Vector Store** | ChromaDB |
| **Data Sources** | AKShare, Tushare Pro |

### Frontend

| Component | Technology |
|-----------|------------|
| **Framework** | Nuxt 4.x |
| **UI** | Vue 3.5+ |
| **UI Components** | Element Plus |
| **State Management** | Pinia |
| **Charts** | ECharts |
| **Language** | TypeScript |

## Project Structure

```
FundAI/
├── app/                        # Backend application
│   ├── api/v1/endpoints/       # API endpoints
│   ├── core/                   # Core configuration
│   │   ├── config.py           # Settings management
│   │   ├── database.py         # Async database engine
│   │   ├── cache.py            # Redis cache
│   │   └── calculations/       # Technical indicators
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic models
│   ├── agents/                 # Multi-agent system
│   │   ├── base.py             # BaseAgent implementation
│   │   ├── orchestrator.py     # Agent orchestration
│   │   ├── fundamental.py      # Fundamental analyst
│   │   ├── technical.py        # Technical analyst
│   │   ├── risk.py             # Risk analyst
│   │   ├── cost.py             # Cost analyst
│   │   ├── sentiment.py        # Sentiment analyst
│   │   ├── decision.py         # Decision analyst
│   │   ├── prompts/            # System prompts
│   │   └── tools/              # Agent tools
│   ├── data_sources/           # Data source adapters
│   ├── services/               # Business services
│   └── main.py                 # Application entry
├── frontend/                   # Frontend application
│   ├── app/                    # Nuxt app directory
│   │   ├── components/         # Vue components
│   │   ├── composables/        # Composable functions
│   │   ├── pages/              # Page routes
│   │   ├── services/           # API services
│   │   ├── stores/             # Pinia stores
│   │   └── utils/              # Utility functions
│   ├── server/                 # Nuxt server
│   └── nuxt.config.ts          # Nuxt configuration
├── database/                   # Database scripts
├── tests/                      # Test modules
├── requirements.txt            # Backend dependencies
└── README.md                   # Project documentation
```

## Quick Start

### Prerequisites

Ensure the following are installed:
- Python 3.12+
- Node.js 22+
- PostgreSQL 15+
- Redis 7.0+

### Backend Setup

```powershell
# Create virtual environment
python -m venv venv
.\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
copy .env.example .env
# Edit .env file to configure database connection and other settings

# Initialize database
# Execute database/init_db.sql

# Start backend server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```powershell
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### Access the Application

- Frontend Application: http://localhost:3000
- Backend API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/auth/send-code | Send verification code |
| POST | /api/v1/auth/register | User registration |
| POST | /api/v1/auth/login | User login |
| POST | /api/v1/auth/logout | User logout |
| POST | /api/v1/auth/refresh | Refresh token |

### Funds

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/funds/search | Search funds |
| GET | /api/v1/funds/{fund_code} | Get fund details |
| GET | /api/v1/funds/{fund_code}/nav | Get NAV history |
| GET | /api/v1/funds/{fund_code}/holdings | Get holdings information |
| GET | /api/v1/funds/{fund_code}/fees | Get fee information |

### Analysis

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/analysis/sessions | Create analysis session |
| GET | /api/v1/analysis/sessions/{session_id}/stream | SSE streaming analysis |
| GET | /api/v1/analysis/sessions/{session_id}/report | Get analysis report |

### Sessions

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | /api/v1/sessions | Get session list |
| GET | /api/v1/sessions/{session_id} | Get session details |

## Development

### Backend Development

```powershell
# Run tests
pytest

# Code formatting
black app/
isort app/
```

### Frontend Development

```powershell
cd frontend

# Build for production
npm run build

# Preview production build
npm run preview

# Type checking
npm run typecheck
```

## Docker Deployment

```powershell
# Start PostgreSQL + Redis + Application
docker-compose up -d
```

## Core Architecture

### Multi-Agent System

- **5 Analytical Agents** execute in parallel/series: Fundamental, Technical, Risk, Cost, Sentiment
- **1 Decision Agent** synthesizes all analysis results and provides short-term/long-term investment recommendations
- Each agent is LLM-driven with tool invocation and RAG knowledge enhancement capabilities
- Agents push SSE events to frontend through `EventCallback`

### Analysis Workflow

1. Build context (fetch fund data → data quality validation → data provenance tagging)
2. Execute 5 analytical agents in parallel
3. **Debate Mechanism**: Detect scoring divergence (threshold 1.5), diverging parties review each other and adjust scores
4. Decision agent synthesizes scores and generates investment recommendations
5. Historical results stored in `AgentMemory` for future reference

### SSE Streaming

- Real-time event pushing via `EventCallback` + `asyncio.Queue`
- Event types: agent status changes, thinking process, tool calls, deep reasoning, debate rounds, progressive updates
- Frontend subscribes via `EventSource` with pause/resume support

### API Proxy

- Frontend Nuxt proxies all `/api/v1/*` requests to backend via `server/routes/api/v1/[...].ts`
- Frontend uses `process.env.NUXT_API_URL` or defaults to `http://localhost:8000`

### LLM Configuration

- LLM settings managed through frontend settings page, stored in `data/config.json`
- Supports any OpenAI-compatible API (API URL, API Key, model name, temperature, etc.)
- Configuration takes effect immediately without service restart

### Data Sources

- Supports AKShare and Tushare Pro data sources
- `DataSourceManager` provides unified management with auto-switching and caching

## Testing Strategy

- **Framework**: pytest + pytest-asyncio (asyncio_mode = auto)
- **Database**: In-memory SQLite with automatic table creation/cleanup per test
- **HTTP Client**: httpx.AsyncClient + ASGITransport for direct ASGI application calls
- **Key Mock Fixtures**: mock_llm_service, mock_datasource_manager, mock_rag_service
- **Test Organization**: tests/ organized by module (test_agents/, test_api/, test_core/, etc.)

## License

MIT License - see [LICENSE](LICENSE) file for details.