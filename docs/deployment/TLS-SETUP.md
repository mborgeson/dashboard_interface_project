# TLS Setup for Production

This document describes how to enable HTTPS for the B&R Capital Dashboard production deployment.

## Architecture

Nginx terminates TLS and proxies to the backend over the internal Docker network (plain HTTP). The configuration:

1. **Port 80** -- Redirects all HTTP requests to HTTPS (301)
2. **Port 443** -- Serves the React app and proxies `/api/*` to the backend over SSL
3. **HSTS header** -- `max-age=63072000; includeSubDomains; preload` (2 years)

## Certificate Placement

Place your TLS certificate files in the `certs/` directory at the project root:

```
dashboard_interface_project/
  certs/
    fullchain.pem    # Full certificate chain (server cert + intermediates)
    privkey.pem      # Private key (keep permissions restrictive)
```

The `docker-compose.prod.yml` mounts `./certs` as `/etc/nginx/ssl:ro` (read-only) in the frontend container.

**Important:** Never commit certificate files to git. The `certs/` directory should be in `.gitignore`.

## Option A: Let's Encrypt (Certbot)

For a server with a public DNS record pointing to it:

```bash
# Install certbot
sudo apt install certbot

# Obtain certificate (standalone mode -- stop nginx first)
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Copy certs to project directory
sudo cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ./certs/fullchain.pem
sudo cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ./certs/privkey.pem
sudo chmod 644 ./certs/fullchain.pem
sudo chmod 600 ./certs/privkey.pem
```

### Auto-Renewal

Let's Encrypt certificates expire every 90 days. Set up a cron job:

```bash
# /etc/cron.d/certbot-renew
0 3 * * 1 root certbot renew --deploy-hook "cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /path/to/project/certs/fullchain.pem && cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /path/to/project/certs/privkey.pem && docker compose -f docker-compose.prod.yml restart frontend"
```

## Option B: Self-Signed Certificate (Development/Internal Only)

For internal or staging deployments where a trusted CA cert is not needed:

```bash
mkdir -p certs
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout certs/privkey.pem \
  -out certs/fullchain.pem \
  -subj "/CN=dashboard.local/O=B&R Capital"
```

Browsers will show a warning for self-signed certs. This is acceptable for internal staging only.

## Option C: Fronting Reverse Proxy

If the dashboard sits behind a load balancer or reverse proxy that already terminates TLS (e.g., AWS ALB, Cloudflare, Traefik):

1. The fronting proxy handles TLS termination
2. It forwards plain HTTP to the dashboard's port 80
3. In this case, you can modify `nginx.conf` to skip the HTTPS server block and serve on port 80 directly (revert to the pre-TLS configuration)

Alternatively, use the current config and have the fronting proxy connect to port 443 with the dashboard's self-signed cert (proxy-to-backend TLS).

## Verifying TLS Configuration

After deploying with certificates:

```bash
# Start production stack
docker compose -f docker-compose.prod.yml up -d

# Test HTTP redirect
curl -I http://yourdomain.com
# Expected: 301 Moved Permanently, Location: https://...

# Test HTTPS
curl -I https://yourdomain.com
# Expected: 200 OK, Strict-Transport-Security header present

# Test SSL configuration
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com < /dev/null 2>/dev/null | openssl x509 -noout -dates
```

## SSL Protocol and Cipher Configuration

The nginx config uses Mozilla's recommended "Intermediate" TLS settings:

- **Protocols:** TLSv1.2, TLSv1.3
- **Ciphers:** ECDHE-based AEAD ciphers only (AES-128-GCM, AES-256-GCM)
- **Session:** 1-day timeout, shared 10MB cache, no session tickets
- **Preference:** Client cipher preference (server does not force order)

This balances security with compatibility for modern browsers and API clients.
