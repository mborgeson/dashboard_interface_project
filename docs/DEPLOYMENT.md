# B&R Capital Dashboard Interface - Deployment Guide

This guide covers deploying the B&R Capital Dashboard Interface application, including both local development setup and production deployment.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development Setup](#local-development-setup)
- [Environment Configuration](#environment-configuration)
- [Database Setup](#database-setup)
- [Running the Application](#running-the-application)
- [Production Deployment](#production-deployment)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Recommended | Purpose |
|----------|----------------|-------------|---------|
| Python | 3.11+ | 3.12 | Backend runtime |
| Node.js | 20+ | 22 LTS | Frontend build/dev |
| PostgreSQL | 15+ | 16 | Primary database |
| Redis | 7+ | 7.2 | Caching & rate limiting |
| Docker | 24+ | Latest | Containerization |
| Docker Compose | 2.20+ | Latest | Multi-container orchestration |

### Optional Software

- **Git**: Version control
- **Make**: Build automation (optional)
- **nginx**: Production reverse proxy

---

## Quick Start (Docker)

The fastest way to get the application running locally:

```bash
# Clone the repository
git clone <repository-url>
cd dashboard_interface_project

# Copy environment file and configure
cp backend/.env.example backend/.env
# Edit backend/.env with your settings (see Environment Configuration)

# Start all services with Docker Compose
docker-compose up -d

# The application will be available at:
# - Frontend: http://localhost:5173
# - Backend API: http://localhost:8000
# - API Documentation: http://localhost:8000/docs
```

### Docker Compose Services

The `docker-compose.yml` includes:

- **backend**: FastAPI application
- **frontend**: React/Vite application
- **postgres**: PostgreSQL database
- **redis**: Redis cache

---

## Local Development Setup

### Backend Setup

1. **Create Python virtual environment**:

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
.\venv\Scripts\activate
```

2. **Install dependencies**:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

3. **Configure environment**:

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# At minimum, set:
# - SECRET_KEY (generate with: python -c "import secrets; print(secrets.token_urlsafe(64))")
# - DATABASE_URL (your PostgreSQL connection string)
```

4. **Set up the database**:

```bash
# Ensure PostgreSQL is running
# Create the database
createdb dashboard_interface_data

# Run migrations
alembic upgrade head
```

5. **Start the backend server**:

```bash
# Development mode with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or using Python directly
python -m uvicorn app.main:app --reload
```

### Frontend Setup

1. **Install Node.js dependencies**:

```bash
cd frontend  # or project root if frontend is there

# Install dependencies
npm install
# or
yarn install
# or
pnpm install
```

2. **Configure environment** (if needed):

```bash
# Create .env file for frontend
cp .env.example .env.local
```

3. **Start the development server**:

```bash
npm run dev
# or
yarn dev
```

---

## Environment Configuration

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key (64+ chars) | Generate with Python secrets module |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/dbname` |

### Azure AD / SharePoint Integration

For SharePoint integration, configure these variables:

| Variable | Description |
|----------|-------------|
| `AZURE_TENANT_ID` | Azure AD tenant ID |
| `AZURE_CLIENT_ID` | Azure AD application (client) ID |
| `AZURE_CLIENT_SECRET` | Azure AD client secret |
| `SHAREPOINT_SITE_URL` | Full SharePoint site URL |
| `SHAREPOINT_SITE` | SharePoint site name |
| `SHAREPOINT_LIBRARY` | Document library name |

### Email Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `SMTP_HOST` | SMTP server hostname | `smtp.gmail.com` |
| `SMTP_PORT` | SMTP server port | `465` |
| `SMTP_USER` | SMTP username | - |
| `SMTP_PASSWORD` | SMTP password or app password | - |
| `EMAIL_FROM_ADDRESS` | Sender email address | - |

### Complete Reference

See `backend/.env.example` for the complete list of all environment variables with descriptions and defaults.

---

## Database Setup

### Using Alembic Migrations

Alembic manages database schema migrations. Common commands:

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# Rollback all migrations
alembic downgrade base

# Check current migration status
alembic current

# View migration history
alembic history

# Create a new migration
alembic revision --autogenerate -m "Description of changes"
```

### Manual Database Setup

If you need to set up the database manually:

```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE dashboard_interface_data;

# Create user (optional)
CREATE USER dashboard_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE dashboard_interface_data TO dashboard_user;

# Exit psql
\q
```

### Database Backup and Restore

```bash
# Backup
pg_dump -U postgres dashboard_interface_data > backup.sql

# Restore
psql -U postgres dashboard_interface_data < backup.sql
```

---

## Running the Application

### Development Mode

```bash
# Terminal 1: Backend
cd backend
source venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Redis (if not using Docker)
redis-server
```

### Production Mode

```bash
# Backend with Gunicorn
cd backend
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000

# Frontend build
cd frontend
npm run build
# Serve dist/ folder with nginx or similar
```

---

## Production Deployment

### Pre-Deployment Checklist

- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEBUG=false`
- [ ] Generate a strong `SECRET_KEY`
- [ ] Configure production `DATABASE_URL`
- [ ] Set up SSL/TLS certificates
- [ ] Configure proper `CORS_ORIGINS`
- [ ] Set up Redis for caching
- [ ] Configure email settings
- [ ] Set up monitoring and logging
- [ ] Configure backup procedures
- [ ] Review rate limiting settings

### Security Considerations

1. **Secrets Management**:
   - Never commit `.env` files to version control
   - Use environment variables or secrets manager
   - Rotate secrets regularly

2. **Network Security**:
   - Use HTTPS for all traffic
   - Configure firewall rules
   - Use reverse proxy (nginx) in production

3. **Database Security**:
   - Use strong passwords
   - Limit database user permissions
   - Enable SSL for database connections

### Nginx Configuration Example

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    # Frontend
    location / {
        root /var/www/dashboard/dist;
        try_files $uri $uri/ /index.html;
    }

    # Backend API
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

---

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_api/test_extraction.py

# Run tests with verbose output
pytest -v

# Run tests matching pattern
pytest -k "test_extraction"
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

### Code Quality

```bash
# Backend linting
cd backend
ruff check .
ruff format .

# Type checking
mypy app/

# Frontend linting
cd frontend
npm run lint
```

---

## Troubleshooting

### Common Issues

#### Database Connection Errors

```
Error: could not connect to server: Connection refused
```

**Solution**: Ensure PostgreSQL is running and the connection string is correct.

```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Start PostgreSQL
sudo systemctl start postgresql
```

#### Redis Connection Errors

```
Error: Connection refused to redis://localhost:6379
```

**Solution**: Ensure Redis is running.

```bash
# Check Redis status
redis-cli ping

# Start Redis
sudo systemctl start redis
```

#### Migration Errors

```
Error: Can't locate revision identified by 'xxxx'
```

**Solution**: Reset migrations if needed (development only):

```bash
# Check current state
alembic current

# Stamp to a known state
alembic stamp head
```

#### Import Errors

```
ModuleNotFoundError: No module named 'app'
```

**Solution**: Ensure you're in the correct directory and virtual environment is activated.

```bash
cd backend
source venv/bin/activate
export PYTHONPATH=$PYTHONPATH:$(pwd)
```

#### SharePoint Integration Issues

1. Verify Azure AD credentials are correct
2. Check that the app has required permissions
3. Ensure SharePoint site URL is correctly formatted
4. Verify the service principal has access to the SharePoint site

```bash
# Test SharePoint connection
python -c "from app.core.config import settings; print(settings.sharepoint_configured)"
```

### Logs

```bash
# Backend logs (if using systemd)
journalctl -u dashboard-backend -f

# Docker logs
docker-compose logs -f backend

# Application logs
tail -f backend/logs/app.log
```

### Health Checks

```bash
# Check backend health
curl http://localhost:8000/health

# Check API documentation
curl http://localhost:8000/docs

# Check database connectivity
curl http://localhost:8000/api/v1/health/db
```

---

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review application logs
3. Check the project's issue tracker
4. Contact the development team

---

*Last updated: January 2025*
