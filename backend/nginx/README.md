# Nginx Configuration for B&R Capital Backend

## Overview

This directory contains the Nginx reverse proxy configuration for production deployment.

## Files

- `nginx.conf` - Main Nginx configuration
- `ssl/` - SSL certificate directory (not tracked in git)

## Features

- **HTTPS Termination**: SSL/TLS encryption with modern cipher suites
- **Load Balancing**: Least-connection algorithm for backend servers
- **Rate Limiting**: 10 requests/second with burst handling
- **WebSocket Support**: Real-time updates via `/ws` endpoint
- **Gzip Compression**: Automatic compression for text-based responses
- **Security Headers**: XSS protection, content-type sniffing prevention
- **Health Checks**: Proxied health endpoint at `/health`

## SSL Setup

### Development (Self-Signed)

```bash
cd nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout key.pem -out cert.pem \
  -subj "/C=US/ST=Arizona/L=Phoenix/O=B&R Capital/CN=localhost"
```

### Production (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d api.yourdomain.com

# Copy to nginx/ssl/
sudo cp /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem nginx/ssl/cert.pem
sudo cp /etc/letsencrypt/live/api.yourdomain.com/privkey.pem nginx/ssl/key.pem
```

## Usage

Production deployment with nginx:

```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Endpoints

| Path | Description |
|------|-------------|
| `/api/*` | API endpoints (rate limited) |
| `/ws` | WebSocket connections |
| `/docs` | Swagger UI documentation |
| `/redoc` | ReDoc documentation |
| `/health` | Health check endpoint |

## Configuration Notes

- Rate limiting: 10 req/s per IP (burst: 20)
- Max request body: 50MB
- WebSocket timeout: 7 days
- SSL protocols: TLSv1.2, TLSv1.3
