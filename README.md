# Secure Financial Insights Copilot

Enterprise-grade GenAI system for financial document analysis, built with production-level RAG, LLM quality evaluation, and financial compliance guardrails.

## What This Does

Ingests SEC filings (10-K, 10-Q, 8-K) and earnings reports, then provides AI-powered financial analysis with:

- **Citation-injected responses** grounded in source documents
- **Hallucination detection** using LLM-as-judge + entity overlap + semantic similarity
- **Self-consistency scoring** via multi-sample comparison
- **Confidence scoring** based on citation density, specificity, and source coverage
- **PII redaction** using Microsoft Presidio with financial entity patterns
- **Content filtering** blocking investment advice and flagging forward-looking statements
- **Full observability** via Prometheus metrics and Grafana dashboards

## Architecture

```
                    ┌──────────────────────────────────────────────┐
                    │              FastAPI Application              │
                    │         (Structured Logging, CORS)           │
                    └──────────────┬───────────────────────────────┘
                                   │
                    ┌──────────────▼───────────────────────────────┐
                    │          LangGraph Orchestration              │
                    │                                               │
                    │  ┌─────────┐  ┌──────────┐  ┌────────────┐  │
                    │  │Retrieve │─▶│ Generate  │─▶│  Evaluate   │  │
                    │  └─────────┘  └──────────┘  └──────┬─────┘  │
                    │       │                            │         │
                    │       │       ┌──────────┐         │         │
                    │       │       │Regenerate│◀────────┘         │
                    │       │       │(if fail) │  (hallucination   │
                    │       │       └──────────┘   > threshold)    │
                    │       │                            │         │
                    │       │                    ┌───────▼──────┐  │
                    │       │                    │  Guardrails   │  │
                    │       │                    │ (PII + Filter)│  │
                    │       │                    └───────┬──────┘  │
                    │       │                            │         │
                    │       │                    ┌───────▼──────┐  │
                    │       │                    │   Assemble    │  │
                    │       │                    │  (Response)   │  │
                    │       │                    └──────────────┘  │
                    └───────┼──────────────────────────────────────┘
                            │
          ┌─────────────────┼─────────────────────┐
          │                 │                     │
   ┌──────▼──────┐  ┌──────▼──────┐      ┌──────▼──────┐
   │ Hybrid      │  │  OpenAI     │      │ Prometheus  │
   │ Retriever   │  │  GPT-4      │      │ + Grafana   │
   │ (RRF Fusion)│  │  Embeddings │      │ Monitoring  │
   └──────┬──────┘  └─────────────┘      └─────────────┘
          │
   ┌──────▼──────┐
   │  ChromaDB   │
   │ Vector Store│
   └─────────────┘
```

## Key Features

### RAG Pipeline
- **Hybrid retrieval**: Dense (semantic) + sparse (keyword) search with Reciprocal Rank Fusion
- **Section-aware chunking**: Preserves SEC filing structure (Item 1A, Item 7, etc.)
- **Financial table preservation**: Tables are chunked separately with headers
- **Citation injection**: Every response includes `[Source N]` references

### LLM Evaluation Pipeline
- **Hallucination detection**: Three-signal approach (LLM judge, entity overlap, semantic similarity)
- **Self-consistency**: Generates multiple responses and measures agreement
- **Confidence scoring**: Composite score from citation density, specificity, hedging language, retrieval relevance
- **Automatic re-generation**: If hallucination score exceeds threshold, regenerates with same context

### Guardrails
- **PII redaction**: SSN, credit cards, account numbers, emails, phones (Presidio + regex fallback)
- **Investment advice blocking**: Detects and removes buy/sell recommendations
- **Forward-looking statement detection**: Flags and appends regulatory disclaimers
- **Token limit enforcement**

### Monitoring (Prometheus + Grafana)
- LLM latency (p50/p95/p99), token usage, error rates
- Evaluation score distributions (hallucination, consistency, confidence)
- Guardrail trigger rates (PII detections, content filter violations)
- Query throughput by type, end-to-end latency
- Vector store size, document processing throughput

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI, Pydantic v2, uvicorn |
| Orchestration | LangGraph (stateful workflow) |
| LLM | OpenAI GPT-4 Turbo |
| Embeddings | OpenAI text-embedding-3-small |
| Vector Store | ChromaDB (Pinecone-ready) |
| Document Processing | Custom SEC parser, tiktoken-based chunker |
| Evaluation | LLM-as-judge, cosine similarity, entity extraction |
| Guardrails | Microsoft Presidio, regex PII detection, content filtering |
| Monitoring | Prometheus, Grafana |
| Database | PostgreSQL (SQLAlchemy async) |
| Cache | Redis |
| Containerization | Docker, docker-compose |
| IaC | Terraform (AWS ECS Fargate, RDS, ElastiCache, ALB) |
| Testing | pytest, pytest-asyncio |

## Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- OpenAI API key

### Local Development

```bash
# Clone
git clone https://github.com/kd444/-Secure-Financial-Insights-Copilot.git
cd -Secure-Financial-Insights-Copilot

# Environment
cp .env.example .env
# Edit .env with your OpenAI API key

# Install
pip install -e ".[dev]"

# Run
python -m src.main
```

### Docker Compose (Full Stack)

```bash
# Start all services (API, PostgreSQL, Redis, Prometheus, Grafana)
docker-compose up --build

# API:        http://localhost:8000/docs
# Grafana:    http://localhost:3000 (admin/admin)
# Prometheus: http://localhost:9090
```

### Ingest a SEC Filing

```bash
# Download and ingest Apple's latest 10-K from SEC EDGAR
curl -X POST http://localhost:8000/api/v1/documents/ingest/sec \
  -H "Content-Type: application/json" \
  -d '{"ticker": "AAPL", "filing_type": "10-K", "num_filings": 1}'
```

### Query with Evaluation

```bash
curl -X POST http://localhost:8000/api/v1/query/ \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are Apple main risk factors and how do they impact revenue?",
    "query_type": "risk_summary",
    "company_filter": "AAPL",
    "include_evaluation": true
  }'
```

Response includes:
- Grounded analysis with `[Source N]` citations
- Hallucination score, consistency score, confidence score
- Pass/Flag/Fail verdict
- Token usage and cost estimate

## Testing

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v -m integration

# Evaluation golden cases
pytest tests/evaluation/ -v -m evaluation

# All tests with coverage
pytest --cov=src --cov-report=html
```

## AWS Deployment (Terraform)

```bash
cd infrastructure/terraform

# Initialize
terraform init

# Plan
terraform plan -var-file=environments/dev/terraform.tfvars

# Deploy
terraform apply -var-file=environments/dev/terraform.tfvars
```

Deploys: ECS Fargate cluster, ALB, RDS PostgreSQL, ElastiCache Redis, CloudWatch logging, auto-scaling.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/query/` | Financial analysis query with RAG + evaluation |
| POST | `/api/v1/query/stream` | Streaming query (SSE) |
| POST | `/api/v1/documents/ingest` | Ingest raw document text |
| POST | `/api/v1/documents/ingest/sec` | Download + ingest from SEC EDGAR |
| POST | `/api/v1/documents/upload` | Upload document file |
| POST | `/api/v1/evaluation/evaluate` | Evaluate an LLM response |
| GET | `/api/v1/evaluation/metrics` | Aggregated quality metrics |
| GET | `/health` | System health with component status |
| GET | `/metrics` | Prometheus metrics endpoint |

## Project Structure

```
src/
├── api/                    # FastAPI routes and dependencies
│   └── routes/             # query, documents, evaluation, health
├── core/                   # Config, logging, exceptions
├── document_processing/    # SEC parser, chunker, EDGAR downloader
├── rag/                    # Embeddings, vector store, hybrid retriever
├── llm/                    # LLM client, prompt templates
├── evaluation/             # Hallucination detector, consistency scorer,
│                           # confidence scorer, evaluation pipeline
├── guardrails/             # PII redactor, content filter
├── orchestration/          # LangGraph workflow
├── monitoring/             # Prometheus metrics definitions
└── models/                 # Pydantic schemas, SQLAlchemy models

infrastructure/
├── docker/                 # Multi-stage Dockerfile
└── terraform/              # AWS IaC (VPC, ECS, RDS, ElastiCache)
    └── modules/            # vpc, ecs, rds, elasticache

monitoring/
├── prometheus/             # Prometheus config
└── grafana/                # Dashboards and provisioning
    └── dashboards/         # LLM Quality Dashboard JSON

tests/
├── unit/                   # Unit tests for all components
├── integration/            # API integration tests
└── evaluation/             # LLM evaluation golden test cases
```
