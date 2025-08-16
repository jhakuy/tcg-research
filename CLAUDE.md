# TCG Research System

## Project Overview

A comprehensive TCG (Trading Card Game) market analysis and prediction system focused on Pokemon cards. The system ingests data from multiple sources, applies machine learning for price prediction, and provides actionable investment recommendations.

## Architecture

### Sub-Agents (Claude Code)
- **Ingestor**: Pulls data from eBay Browse, PriceCharting, PSA, and TCGdx APIs
- **Entity Resolver**: Matches cards across data sources with strict English-only filtering
- **Analyst**: Generates ML features and market analysis
- **Risk Policy**: Enforces trading limits and quality filters
- **Reporter**: Creates user-facing recommendations and reports

### Data Sources
- **eBay Browse API**: Live market data (active listings, prices)
- **PriceCharting API**: Historical price data and trends
- **PSA API**: Population data for graded cards
- **TCGdx API**: Card catalog and normalization (free, no auth)

### Tech Stack
- **Backend**: Python FastAPI + PostgreSQL/TimescaleDB
- **ML**: CatBoost (handles categorical features well)
- **Entity Resolution**: FuzzyWuzzy for string matching
- **MCP**: Custom servers for API integrations

## Quick Start

1. **Setup Database**:
```bash
docker-compose up -d postgres
```

2. **Install Dependencies**:
```bash
pip install -e .
```

3. **Configure Environment**:
```bash
cp .env.example .env
# Edit .env with your API keys
```

4. **Initialize System**:
```bash
python scripts/setup.py
```

5. **Run API Server**:
```bash
python -m tcg_research.api.main
```

6. **Get Recommendations**:
```bash
curl http://localhost:8000/tcg/scan
```

## API Keys Required

You'll need to obtain:
- **eBay App ID & Cert ID**: [eBay Developers Program](https://developer.ebay.com/)
- **PriceCharting API Key**: [PriceCharting](https://www.pricecharting.com/api)
- **PSA API Key**: [PSA](https://www.psacard.com/publicapi)

TCGdx is free and requires no authentication.

## Commands

- `npm run lint`: Not applicable (Python project)
- `npm run typecheck`: Use `mypy src/` for type checking
- `python -m pytest`: Run tests
- `alembic upgrade head`: Apply database migrations

## Development Notes

- Focus on English cards only for initial implementation
- Entity resolution is critical - bad matching = bad predictions
- Use walk-forward validation to prevent data leakage
- Enforce strict risk limits (min liquidity, max position size)
- Mock API responses included for development without real API keys

## Model Features

### Singles
- Price momentum (30/90/180 day)
- Liquidity metrics (active listings, turnover)
- Bid-ask spread analysis
- PSA population pressure
- Volatility measures

### Sealed Products
- Time since release
- Price slope trends
- Supply proxy (listing trends)
- Discount to MSRP
- Set type classification

## Target Classification
- **BUY**: >10% expected 3-month return
- **WATCH**: -10% to +10% return
- **AVOID**: <-10% return