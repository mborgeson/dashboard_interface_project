#!/usr/bin/env bash
# =============================================================================
# B&R Capital Dashboard - Production Server Setup Script
# =============================================================================
# This script sets up a fresh Ubuntu server for production deployment.
# Run as root or with sudo privileges.
#
# Usage: sudo ./setup-server.sh [OPTIONS]
#   --domain DOMAIN     Domain name for SSL (required for SSL setup)
#   --email EMAIL       Email for Let's Encrypt notifications
#   --skip-docker       Skip Docker installation
#   --skip-nginx        Skip Nginx installation
#   --skip-ssl          Skip SSL setup
#   --skip-firewall     Skip firewall configuration
#   --deploy-user USER  Username for deploy user (default: deploy)
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration
# =============================================================================
readonly SCRIPT_NAME="$(basename "$0")"
readonly SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
readonly LOG_FILE="/var/log/dashboard-setup.log"
readonly DASHBOARD_DIR="/opt/dashboard"
readonly DEFAULT_DEPLOY_USER="deploy"

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# =============================================================================
# Logging Functions
# =============================================================================
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp
    timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
    log "INFO" "$*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
    log "SUCCESS" "$*"
}

log_warn() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
    log "WARNING" "$*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
    log "ERROR" "$*"
}

# =============================================================================
# Helper Functions
# =============================================================================
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root or with sudo"
        exit 1
    fi
}

check_os() {
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine OS. /etc/os-release not found."
        exit 1
    fi

    # shellcheck source=/dev/null
    source /etc/os-release

    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        log_warn "This script is designed for Ubuntu/Debian. Detected: $ID"
        read -rp "Continue anyway? (y/N): " response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi

    log_info "Detected OS: $PRETTY_NAME"
}

command_exists() {
    command -v "$1" &> /dev/null
}

# =============================================================================
# Installation Functions
# =============================================================================
update_system() {
    log_info "Updating system packages..."
    apt-get update -qq
    apt-get upgrade -y -qq
    log_success "System packages updated"
}

install_dependencies() {
    log_info "Installing required dependencies..."
    apt-get install -y -qq \
        apt-transport-https \
        ca-certificates \
        curl \
        gnupg \
        lsb-release \
        software-properties-common \
        git \
        jq \
        unzip \
        htop \
        ncdu \
        fail2ban \
        logrotate
    log_success "Dependencies installed"
}

install_docker() {
    if command_exists docker; then
        log_info "Docker is already installed: $(docker --version)"
        return 0
    fi

    log_info "Installing Docker..."

    # Add Docker's official GPG key
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg

    # Add the repository
    echo \
        "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
        $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        tee /etc/apt/sources.list.d/docker.list > /dev/null

    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    # Start and enable Docker
    systemctl start docker
    systemctl enable docker

    log_success "Docker installed: $(docker --version)"
}

configure_docker() {
    log_info "Configuring Docker..."

    # Create Docker daemon configuration
    mkdir -p /etc/docker
    cat > /etc/docker/daemon.json <<EOF
{
    "log-driver": "json-file",
    "log-opts": {
        "max-size": "10m",
        "max-file": "5"
    },
    "storage-driver": "overlay2",
    "live-restore": true,
    "userland-proxy": false,
    "default-address-pools": [
        {
            "base": "172.17.0.0/16",
            "size": 24
        }
    ]
}
EOF

    # Restart Docker to apply configuration
    systemctl restart docker

    log_success "Docker configured"
}

create_deploy_user() {
    local username="${1:-$DEFAULT_DEPLOY_USER}"

    if id "$username" &>/dev/null; then
        log_info "User '$username' already exists"
    else
        log_info "Creating deploy user: $username"
        useradd -m -s /bin/bash -G docker,sudo "$username"
        log_success "Deploy user '$username' created"
    fi

    # Set up SSH directory
    local ssh_dir="/home/${username}/.ssh"
    mkdir -p "$ssh_dir"
    chmod 700 "$ssh_dir"
    touch "$ssh_dir/authorized_keys"
    chmod 600 "$ssh_dir/authorized_keys"
    chown -R "${username}:${username}" "$ssh_dir"

    # Configure passwordless sudo for docker commands
    cat > "/etc/sudoers.d/${username}" <<EOF
# Allow deploy user to run docker commands without password
${username} ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose, /usr/bin/systemctl restart docker, /usr/bin/systemctl status docker
EOF
    chmod 440 "/etc/sudoers.d/${username}"

    log_success "SSH and sudo configured for '$username'"
    log_warn "Add SSH public key to: $ssh_dir/authorized_keys"
}

setup_directory_structure() {
    log_info "Setting up directory structure at $DASHBOARD_DIR..."

    local deploy_user="${1:-$DEFAULT_DEPLOY_USER}"

    # Create directory structure
    mkdir -p "$DASHBOARD_DIR"/{config,data,logs,backups,nginx/ssl,scripts}
    mkdir -p "$DASHBOARD_DIR"/data/{postgres,redis}

    # Set ownership
    chown -R "${deploy_user}:${deploy_user}" "$DASHBOARD_DIR"
    chmod -R 755 "$DASHBOARD_DIR"
    chmod 700 "$DASHBOARD_DIR"/nginx/ssl

    # Create placeholder files
    cat > "$DASHBOARD_DIR/README.md" <<EOF
# B&R Capital Dashboard - Production Deployment

## Directory Structure
- config/     - Configuration files
- data/       - Persistent data (database, redis)
- logs/       - Application logs
- backups/    - Database and configuration backups
- nginx/      - Nginx configuration and SSL certificates
- scripts/    - Deployment and maintenance scripts

## Quick Commands
- Deploy: ./scripts/deploy.sh
- Logs: docker compose logs -f
- Status: docker compose ps

## Important
- Never edit .env directly on server - use CI/CD secrets
- Backups run daily at 2 AM
- SSL certificates auto-renew via certbot
EOF

    log_success "Directory structure created at $DASHBOARD_DIR"
}

configure_firewall() {
    log_info "Configuring UFW firewall..."

    # Install UFW if not present
    if ! command_exists ufw; then
        apt-get install -y -qq ufw
    fi

    # Reset UFW to defaults
    ufw --force reset

    # Default policies
    ufw default deny incoming
    ufw default allow outgoing

    # Allow SSH (important - do this first!)
    ufw allow 22/tcp comment 'SSH'

    # Allow HTTP and HTTPS
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'

    # Enable UFW
    ufw --force enable

    # Show status
    ufw status verbose

    log_success "Firewall configured"
}

install_nginx() {
    if command_exists nginx; then
        log_info "Nginx is already installed: $(nginx -v 2>&1)"
        return 0
    fi

    log_info "Installing Nginx..."
    apt-get install -y -qq nginx

    # Stop nginx (we'll configure it first)
    systemctl stop nginx

    log_success "Nginx installed"
}

configure_nginx() {
    local domain="${1:-}"

    log_info "Configuring Nginx as reverse proxy..."

    # Backup default config
    if [[ -f /etc/nginx/sites-enabled/default ]]; then
        rm /etc/nginx/sites-enabled/default
    fi

    # Create main Nginx config
    cat > /etc/nginx/nginx.conf <<'EOF'
user www-data;
worker_processes auto;
pid /run/nginx.pid;
include /etc/nginx/modules-enabled/*.conf;

events {
    worker_connections 1024;
    use epoll;
    multi_accept on;
}

http {
    # Basic Settings
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    server_tokens off;

    # MIME Types
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    # Logging
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time uct="$upstream_connect_time" '
                    'uht="$upstream_header_time" urt="$upstream_response_time"';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Gzip Settings
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types text/plain text/css text/xml application/json application/javascript
               application/xml application/rss+xml application/atom+xml image/svg+xml;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Rate Limiting
    limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
    limit_conn_zone $binary_remote_addr zone=conn_limit:10m;

    # Upstream Backends
    upstream backend_api {
        server 127.0.0.1:8000;
        keepalive 32;
    }

    upstream frontend_app {
        server 127.0.0.1:3000;
        keepalive 16;
    }

    # Include site configurations
    include /etc/nginx/conf.d/*.conf;
    include /etc/nginx/sites-enabled/*;
}
EOF

    # Create site configuration
    local site_config="/etc/nginx/sites-available/dashboard"

    if [[ -n "$domain" ]]; then
        # Configuration with domain
        cat > "$site_config" <<EOF
# HTTP - Redirect to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name ${domain} www.${domain};

    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

# HTTPS - Main Configuration
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name ${domain} www.${domain};

    # SSL Configuration (will be updated by certbot)
    ssl_certificate /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_session_timeout 1d;
    ssl_session_cache shared:SSL:50m;
    ssl_session_tickets off;

    # Modern SSL Configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # API Proxy
    location /api/ {
        limit_req zone=api_limit burst=50 nodelay;
        limit_conn conn_limit 20;

        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }

    # Health Check Endpoint
    location /health {
        proxy_pass http://backend_api/health;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        access_log off;
    }

    # WebSocket Support (for real-time features)
    location /ws/ {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }

    # Frontend Application
    location / {
        proxy_pass http://frontend_app;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header Connection "";

        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {
            proxy_pass http://frontend_app;
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Error Pages
    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
    }
}
EOF
    else
        # Configuration without domain (IP-based)
        cat > "$site_config" <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    # API Proxy
    location /api/ {
        limit_req zone=api_limit burst=50 nodelay;
        limit_conn conn_limit 20;

        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";

        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health Check Endpoint
    location /health {
        proxy_pass http://backend_api/health;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        access_log off;
    }

    # WebSocket Support
    location /ws/ {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }

    # Frontend Application
    location / {
        proxy_pass http://frontend_app;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Connection "";
    }

    error_page 500 502 503 504 /50x.html;
    location = /50x.html {
        root /usr/share/nginx/html;
        internal;
    }
}
EOF
    fi

    # Enable site
    ln -sf "$site_config" /etc/nginx/sites-enabled/dashboard

    # Test configuration
    nginx -t

    # Create certbot webroot directory
    mkdir -p /var/www/certbot

    log_success "Nginx configured"
}

setup_ssl() {
    local domain="$1"
    local email="$2"

    if [[ -z "$domain" ]]; then
        log_warn "No domain specified, skipping SSL setup"
        return 0
    fi

    log_info "Setting up SSL with Let's Encrypt for $domain..."

    # Install certbot
    if ! command_exists certbot; then
        apt-get install -y -qq certbot python3-certbot-nginx
    fi

    # Create self-signed certificate first (for initial nginx startup)
    local ssl_dir="/etc/nginx/ssl"
    mkdir -p "$ssl_dir"

    if [[ ! -f "$ssl_dir/fullchain.pem" ]]; then
        log_info "Creating temporary self-signed certificate..."
        openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
            -keyout "$ssl_dir/privkey.pem" \
            -out "$ssl_dir/fullchain.pem" \
            -subj "/CN=$domain"
    fi

    # Start nginx for ACME challenge
    systemctl start nginx

    # Obtain Let's Encrypt certificate
    local certbot_args=(
        "--nginx"
        "-d" "$domain"
        "--non-interactive"
        "--agree-tos"
        "--redirect"
    )

    if [[ -n "$email" ]]; then
        certbot_args+=("-m" "$email")
    else
        certbot_args+=("--register-unsafely-without-email")
    fi

    if certbot "${certbot_args[@]}"; then
        log_success "SSL certificate obtained successfully"

        # Setup auto-renewal
        systemctl enable certbot.timer
        systemctl start certbot.timer

        # Create renewal hook to reload nginx
        cat > /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh <<'EOF'
#!/bin/bash
systemctl reload nginx
EOF
        chmod +x /etc/letsencrypt/renewal-hooks/deploy/reload-nginx.sh

        log_success "SSL auto-renewal configured"
    else
        log_error "Failed to obtain SSL certificate"
        log_warn "Using self-signed certificate. Run certbot manually later."
    fi
}

configure_fail2ban() {
    log_info "Configuring Fail2ban..."

    # Create jail configuration
    cat > /etc/fail2ban/jail.local <<'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
ignoreip = 127.0.0.1/8

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
bantime = 7200

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
port = http,https
logpath = /var/log/nginx/error.log
maxretry = 10
findtime = 60
bantime = 600
EOF

    # Restart fail2ban
    systemctl restart fail2ban
    systemctl enable fail2ban

    log_success "Fail2ban configured"
}

setup_logrotate() {
    log_info "Configuring log rotation..."

    cat > /etc/logrotate.d/dashboard <<EOF
/opt/dashboard/logs/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 deploy deploy
    sharedscripts
    postrotate
        docker compose -f /opt/dashboard/docker-compose.prod.yml kill -s USR1 backend 2>/dev/null || true
    endscript
}
EOF

    log_success "Log rotation configured"
}

# =============================================================================
# Main Script
# =============================================================================
main() {
    local domain=""
    local email=""
    local deploy_user="$DEFAULT_DEPLOY_USER"
    local skip_docker=false
    local skip_nginx=false
    local skip_ssl=false
    local skip_firewall=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --domain)
                domain="$2"
                shift 2
                ;;
            --email)
                email="$2"
                shift 2
                ;;
            --deploy-user)
                deploy_user="$2"
                shift 2
                ;;
            --skip-docker)
                skip_docker=true
                shift
                ;;
            --skip-nginx)
                skip_nginx=true
                shift
                ;;
            --skip-ssl)
                skip_ssl=true
                shift
                ;;
            --skip-firewall)
                skip_firewall=true
                shift
                ;;
            -h|--help)
                echo "Usage: $SCRIPT_NAME [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --domain DOMAIN     Domain name for SSL"
                echo "  --email EMAIL       Email for Let's Encrypt"
                echo "  --deploy-user USER  Deploy username (default: deploy)"
                echo "  --skip-docker       Skip Docker installation"
                echo "  --skip-nginx        Skip Nginx installation"
                echo "  --skip-ssl          Skip SSL setup"
                echo "  --skip-firewall     Skip firewall configuration"
                echo "  -h, --help          Show this help"
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Initialize log file
    mkdir -p "$(dirname "$LOG_FILE")"
    touch "$LOG_FILE"

    echo ""
    echo "=============================================="
    echo "  B&R Capital Dashboard - Server Setup"
    echo "=============================================="
    echo ""

    # Pre-flight checks
    check_root
    check_os

    log_info "Starting server setup..."
    log_info "Domain: ${domain:-'Not specified'}"
    log_info "Deploy user: $deploy_user"

    # Run installation steps
    update_system
    install_dependencies

    if [[ "$skip_docker" != true ]]; then
        install_docker
        configure_docker
    fi

    create_deploy_user "$deploy_user"
    setup_directory_structure "$deploy_user"

    if [[ "$skip_firewall" != true ]]; then
        configure_firewall
    fi

    if [[ "$skip_nginx" != true ]]; then
        install_nginx
        configure_nginx "$domain"

        if [[ "$skip_ssl" != true && -n "$domain" ]]; then
            setup_ssl "$domain" "$email"
        fi

        systemctl start nginx
        systemctl enable nginx
    fi

    configure_fail2ban
    setup_logrotate

    echo ""
    echo "=============================================="
    echo "  Setup Complete!"
    echo "=============================================="
    echo ""
    echo "Next steps:"
    echo "1. Add SSH public key to: /home/${deploy_user}/.ssh/authorized_keys"
    echo "2. Copy deployment files to: $DASHBOARD_DIR"
    echo "3. Create .env file from .env.example"
    echo "4. Run deploy.sh to start services"
    echo ""
    echo "Log file: $LOG_FILE"
    echo ""

    log_success "Server setup completed successfully"
}

# Run main function
main "$@"
