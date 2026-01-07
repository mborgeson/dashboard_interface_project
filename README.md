# B&R Capital Dashboard Interface

A comprehensive real estate investment dashboard for B&R Capital, featuring automated data extraction from SharePoint, financial analytics, and portfolio management.

## Features

- Real-time portfolio dashboard with key metrics
- Automated SharePoint integration for UW model extraction
- Financial data visualization and reporting
- Interest rate and economic data integration (FRED API)
- WebSocket support for live updates
- Role-based access control

## Tech Stack

**Backend:**
- Python 3.11+ with FastAPI
- PostgreSQL 15+ database
- Redis for caching and rate limiting
- SQLAlchemy + Alembic for ORM and migrations

**Frontend:**
- React 18+ with TypeScript
- Vite for build tooling
- TailwindCSS for styling

## Quick Start

```bash
# Clone repository
git clone <repository-url>
cd dashboard_interface_project

# Configure environment
cp backend/.env.example backend/.env
# Edit backend/.env with your settings

# Start with Docker
docker-compose up -d

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000/docs
```

## Documentation

- [Deployment Guide](docs/DEPLOYMENT.md) - Complete setup and deployment instructions
- [API Documentation](http://localhost:8000/docs) - Interactive API docs (when running)

## Development

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
npm install
npm run dev
```

## Testing

```bash
# Backend tests
cd backend
pytest --cov=app

# Frontend tests
npm run test
```

## License

Proprietary - B&R Capital
