# Production Deployment Quick Reference Card

## 🚀 Quick Start (5 Minutes)

### 1. Prepare Environment Variables
```bash
# Copy template to .env
cp .env.example .env

# Edit with production secrets
nano .env

# Essential variables to customize:
# - POSTGRES_PASSWORD (generate: openssl rand -base64 32)
# - REDIS_PASSWORD (generate: openssl rand -base64 32)
# - SECRET_KEY (generate: python -c "import secrets; print(secrets.token_urlsafe(64))")
# - CORS_ORIGINS (your production domain)
# - VITE_API_URL (your API domain)
```

### 2. Validate Configuration
```bash
docker-compose -f docker-compose.prod.yml config
```

### 3. Build and Start
```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services in background
docker-compose -f docker-compose.prod.yml up -d

# Check health
docker-compose -f docker-compose.prod.yml ps
```

### 4. Verify Services
```bash
# Follow logs in real-time
docker-compose -f docker-compose.prod.yml logs -f

# Test specific service
docker exec dashboard-backend-prod curl localhost:8000/health
```

---

## 📋 Environment Variables Checklist

### Critical (Must Configure)
- [ ] `POSTGRES_PASSWORD` - Strong password for PostgreSQL
- [ ] `REDIS_PASSWORD` - Strong password for Redis
- [ ] `SECRET_KEY` - 64+ character random string for application secrets
- [ ] `CORS_ORIGINS` - Your production domain(s)
- [ ] `VITE_API_URL` - Backend API URL for frontend (https://api.yourdomain.com)

### Important (Strongly Recommended)
- [ ] `POSTGRES_USER` - PostgreSQL username (default: postgres)
- [ ] `BACKEND_WORKERS` - Uvicorn worker count (default: 4)
- [ ] `FRONTEND_PORT` - Frontend port (default: 80)
- [ ] `VITE_WS_URL` - WebSocket URL (wss://api.yourdomain.com)

### Optional
- [ ] `LOG_LEVEL` - Application log level (default: info)
- [ ] `REDIS_CACHE_TTL` - Cache expiration in seconds (default: 3600)
- [ ] `RATE_LIMIT_ENABLED` - Enable rate limiting (default: true)
- [ ] Email/Azure/External API keys - Only if using those features

---

## 🔐 Security Verification Checklist

Before deploying to production:

```bash
# 1. Verify no secrets in git
git grep "your_" -- '*.env' '*.md'  # Should return nothing

# 2. Check .env file permissions
ls -la .env  # Should be: -rw------- (600)

# 3. Verify DEBUG is false
grep DEBUG .env

# 4. Verify all required passwords are set
grep -E "POSTGRES_PASSWORD|REDIS_PASSWORD|SECRET_KEY" .env

# 5. Check nginx security headers
curl -I http://localhost/ | grep -E "X-Frame-Options|X-Content-Type-Options"
```

---

## 📊 Health Check Commands

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Check PostgreSQL
docker exec dashboard-postgres-prod pg_isready -U postgres

# Check Redis
docker exec dashboard-redis-prod redis-cli -a REDIS_PASSWORD ping

# Check Backend API
docker exec dashboard-backend-prod curl -f localhost:8000/health

# Check Frontend
curl -f http://localhost/

# View detailed logs
docker-compose -f docker-compose.prod.yml logs --tail=100
```

---

## 🐛 Troubleshooting

### Service won't start
```bash
# View error logs
docker-compose -f docker-compose.prod.yml logs <service_name>

# Common issues:
# - Port already in use: Change FRONTEND_PORT in .env
# - Missing environment variable: Check .env file
# - Image build failed: Run `docker-compose build --no-cache`
```

### Health check failures
```bash
# Increase timeouts in docker-compose.prod.yml if services are slow:
healthcheck:
  timeout: 15s  # Was 10s
  start_period: 45s  # Was 30s
```

### Database connection issues
```bash
# Verify PostgreSQL is running
docker exec dashboard-postgres-prod pg_isready -U ${POSTGRES_USER}

# Check credentials in .env match docker-compose.prod.yml
```

### Frontend can't connect to backend
```bash
# Verify VITE_API_URL in .env is correct
# Check nginx proxy configuration in nginx.conf
# Verify backend health: curl http://localhost:8000/health
```

---

## 📈 Monitoring Commands

```bash
# Real-time resource usage
docker stats dashboard-*

# Container metrics
docker ps --format "table {{.Names}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# View last 50 log lines
docker-compose -f docker-compose.prod.yml logs --tail=50

# Follow logs for specific service
docker-compose -f docker-compose.prod.yml logs -f backend
```

---

## 🔄 Common Operations

### Restart a service
```bash
docker-compose -f docker-compose.prod.yml restart backend
```

### View environment variables in container
```bash
docker exec dashboard-backend-prod env | grep -E "^(DATABASE_|REDIS_|SECRET_)"
```

### Execute command in container
```bash
docker exec dashboard-backend-prod python -m pytest
```

### View container resource limits
```bash
docker inspect dashboard-backend-prod --format='{{.HostConfig.Memory}}'
```

### Create database backup
```bash
docker exec dashboard-postgres-prod pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} > backup.sql
```

### Restore database backup
```bash
docker exec -i dashboard-postgres-prod psql -U ${POSTGRES_USER} ${POSTGRES_DB} < backup.sql
```

---

## 🛑 Shutdown and Cleanup

### Stop all services (keep data)
```bash
docker-compose -f docker-compose.prod.yml down
```

### Stop all services and remove volumes (DELETE DATA!)
```bash
docker-compose -f docker-compose.prod.yml down -v
```

### Remove unused images and volumes
```bash
docker system prune --volumes
```

---

## 📁 Important Files and Their Locations

| Purpose | Location |
|---------|----------|
| Production Compose | `docker-compose.prod.yml` |
| Environment Template | `.env.example` |
| Backend Dockerfile | `backend/Dockerfile` |
| Frontend Dockerfile | `Dockerfile.frontend` |
| Nginx Config | `nginx.conf` |
| Verification Report | `DOCKER_PRODUCTION_VERIFICATION.md` |
| Deployment Script | `scripts/deployment/deploy.sh` |
| Setup Script | `scripts/deployment/setup-server.sh` |

---

## 📞 Support and Documentation

- **Detailed Report**: See `DOCKER_PRODUCTION_VERIFICATION.md`
- **Deployment Scripts**: `scripts/deployment/deploy.sh`
- **Docker Documentation**: https://docs.docker.com/
- **Docker Compose Reference**: https://docs.docker.com/compose/reference/

---

## 🎯 Production Readiness Checklist

Before going live:

- [ ] `.env` file created with all required passwords
- [ ] `docker-compose config` validates without errors
- [ ] All services passing health checks
- [ ] Frontend loads and connects to backend
- [ ] API endpoints responding correctly
- [ ] Nginx security headers present
- [ ] No debug output in production logs
- [ ] Database and Redis data persistence verified
- [ ] Backup strategy in place
- [ ] Monitoring/alerting configured
- [ ] SSL/TLS termination configured (recommended)
- [ ] Resource limits tested under load

---

**Version**: 1.0
**Last Updated**: February 12, 2026
**Status**: Production Ready ✅
