# TCG Research System

AI-powered Pokemon card market analysis and investment recommendations.

## Features

- **Real-time Market Analysis**: Ingests data from eBay, PriceCharting, PSA, and TCGdx APIs
- **ML-Powered Predictions**: CatBoost models for 3-month return forecasting
- **Entity Resolution**: Matches cards across data sources (English cards only)
- **Investment Recommendations**: BUY/WATCH/AVOID signals with confidence scores
- **Risk Management**: Built-in position limits and quality filters
- **Web Interface**: Clean dashboard for viewing recommendations

## Architecture

### Backend (Python/FastAPI)
- **Sub-agents**: Specialized agents for ingestion, analysis, and recommendations
- **ML Pipeline**: CatBoost with walk-forward validation
- **Database**: PostgreSQL with TimescaleDB for time-series data
- **APIs**: RESTful endpoints for data access

### Frontend (Next.js/React)
- **Dashboard**: Real-time recommendation display
- **Responsive**: Works on desktop and mobile
- **TypeScript**: Full type safety

## Quick Start

### Option 1: Full Stack (Recommended)

1. **Install dependencies**:
```bash
npm install
pip install -e .
```

2. **Start database**:
```bash
docker-compose up -d postgres
```

3. **Start API server**:
```bash
python -m uvicorn tcg_research.api.main:app --reload
```

4. **Start frontend**:
```bash
npm run dev
```

5. **Visit**: http://localhost:3000

### Option 2: API Only

1. **Start with Docker**:
```bash
docker-compose up
```

2. **Access API**: http://localhost:8000
3. **Try endpoint**: http://localhost:8000/tcg/scan

## API Endpoints

- `GET /tcg/scan` - Main recommendation endpoint
- `GET /predictions/buy` - BUY recommendations only
- `GET /cards` - List tracked cards
- `POST /cards/ingest` - Add new card to tracking
- `POST /model/train` - Train ML models
- `GET /health` - Health check

## Environment Variables

⚠️ **SECURITY**: Copy `.env.example` to `.env` and add your real API keys. Never commit `.env` to Git.

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

Required variables:
```bash
DATABASE_URL=postgresql://user:password@localhost:5432/tcg_research
EBAY_APP_ID=your_actual_app_id
EBAY_CERT_ID=your_actual_cert_id
PRICECHARTING_API_KEY=your_actual_key
PSA_API_KEY=your_actual_key
```

## Deployment

### Vercel (Frontend + API)
```bash
vercel --prod
```

### Docker
```bash
docker build -t tcg-research .
docker run -p 8000:8000 tcg-research
```

## Development Notes

- **Mock Data**: System works without API keys (returns mock data)
- **Entity Resolution**: English cards only for MVP
- **OAuth Required**: eBay API needs OAuth2 for production
- **Model Training**: Requires historical data for meaningful predictions

## Tech Stack

**Backend**: Python, FastAPI, SQLAlchemy, CatBoost, PostgreSQL, TimescaleDB
**Frontend**: Next.js, React, TypeScript, Tailwind CSS
**APIs**: eBay Browse, PriceCharting, PSA, TCGdx
**Deployment**: Vercel, Docker

## Contributing

This system is designed for educational purposes. Not financial advice.

## License

MIT