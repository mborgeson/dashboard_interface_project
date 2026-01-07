# GitHub Secrets Setup Guide

This guide documents all secrets and variables required for the deployment workflow defined in `.github/workflows/deploy.yml`.

## Overview

The deployment workflow uses GitHub Actions to build Docker images and deploy to staging and production environments via SSH. Proper secret configuration is essential for secure, automated deployments.

## Required Secrets

### 1. DEPLOY_SSH_KEY

**Description:** SSH private key used to authenticate with deployment servers.

**Scope:** Repository-level (shared across all environments)

**How to Generate:**

```bash
# Generate a dedicated deployment key (Ed25519 recommended for security)
ssh-keygen -t ed25519 -C "github-deploy@your-repo" -f deploy_key -N ""

# Alternative: RSA key if Ed25519 is not supported
ssh-keygen -t rsa -b 4096 -C "github-deploy@your-repo" -f deploy_key -N ""
```

This creates two files:
- `deploy_key` - Private key (add to GitHub Secrets)
- `deploy_key.pub` - Public key (add to server's authorized_keys)

**How to Add:**

1. Navigate to your repository on GitHub
2. Go to **Settings** > **Secrets and variables** > **Actions**
3. Click **New repository secret**
4. Name: `DEPLOY_SSH_KEY`
5. Value: Paste the entire contents of `deploy_key` (including `-----BEGIN` and `-----END` lines)
6. Click **Add secret**

**Server Setup:**

On each deployment server, add the public key to the deploy user:

```bash
# On staging/production server
sudo mkdir -p /home/deploy/.ssh
sudo chmod 700 /home/deploy/.ssh
echo "ssh-ed25519 AAAA... github-deploy@your-repo" | sudo tee -a /home/deploy/.ssh/authorized_keys
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
```

---

### 2. STAGING_HOST

**Description:** Hostname or IP address of the staging server.

**Scope:** Repository-level or Staging environment

**Example Values:**
- `staging.example.com`
- `192.168.1.100`
- `staging-server.internal.example.com`

**How to Add:**

1. Navigate to **Settings** > **Secrets and variables** > **Actions**
2. Click **New repository secret**
3. Name: `STAGING_HOST`
4. Value: Your staging server hostname or IP
5. Click **Add secret**

**Alternative - Environment-Specific:**

1. Go to **Settings** > **Environments**
2. Select or create **staging** environment
3. Add as an environment secret

---

### 3. PRODUCTION_HOST

**Description:** Hostname or IP address of the production server.

**Scope:** Production environment (recommended for additional protection)

**Example Values:**
- `app.example.com`
- `prod-server.example.com`
- `10.0.0.50`

**How to Add (Recommended - Environment Secret):**

1. Navigate to **Settings** > **Environments**
2. Click **New environment** or select **production**
3. Enable **Required reviewers** (recommended for production)
4. Under **Environment secrets**, click **Add secret**
5. Name: `PRODUCTION_HOST`
6. Value: Your production server hostname or IP
7. Click **Add secret**

---

### 4. DEPLOY_USER (Optional)

**Description:** Username for SSH connections to deployment servers.

**Default:** `deploy` (if not specified)

**Scope:** Repository-level

**When to Configure:**
- Your deployment user is not named `deploy`
- Different users for different environments (use environment secrets)

**How to Add:**

1. Navigate to **Settings** > **Secrets and variables** > **Actions**
2. Click **New repository secret**
3. Name: `DEPLOY_USER`
4. Value: Your deployment username (e.g., `ubuntu`, `deployer`, `ci`)
5. Click **Add secret**

---

## Required Variables

Variables are used for non-sensitive configuration values that can be visible in workflow logs.

### 1. STAGING_URL

**Description:** Base URL of the staging environment for health checks.

**Scope:** Staging environment or repository-level

**Example Values:**
- `https://staging.example.com`
- `https://dashboard-staging.example.com`
- `http://staging.internal:8080`

**How to Add:**

1. Navigate to **Settings** > **Environments**
2. Select **staging** environment
3. Under **Environment variables**, click **Add variable**
4. Name: `STAGING_URL`
5. Value: Your staging URL
6. Click **Add variable**

---

### 2. PRODUCTION_URL

**Description:** Base URL of the production environment for health checks.

**Scope:** Production environment

**Example Values:**
- `https://app.example.com`
- `https://dashboard.example.com`
- `https://www.example.com`

**How to Add:**

1. Navigate to **Settings** > **Environments**
2. Select **production** environment
3. Under **Environment variables**, click **Add variable**
4. Name: `PRODUCTION_URL`
5. Value: Your production URL
6. Click **Add variable**

---

## Environment Configuration

### Setting Up GitHub Environments

1. Navigate to **Settings** > **Environments**
2. Create two environments: `staging` and `production`

#### Staging Environment
- **Protection rules:** Optional
- **Secrets:** `STAGING_HOST` (optional, can be repository-level)
- **Variables:** `STAGING_URL`

#### Production Environment
- **Protection rules:**
  - Enable **Required reviewers** - Add at least one reviewer
  - Optional: **Wait timer** (e.g., 5 minutes delay)
  - Optional: Limit to specific branches (e.g., `main` only)
- **Secrets:** `PRODUCTION_HOST`
- **Variables:** `PRODUCTION_URL`

---

## Security Best Practices

### SSH Key Security

1. **Use dedicated keys:** Never reuse personal SSH keys for deployment
2. **Restrict key permissions:** On servers, limit what the deploy key can do:
   ```bash
   # In authorized_keys, add restrictions:
   command="/opt/scripts/deploy.sh",no-port-forwarding,no-X11-forwarding,no-agent-forwarding ssh-ed25519 AAAA...
   ```
3. **Rotate keys regularly:** Schedule quarterly key rotation
4. **Audit access:** Review authorized_keys files periodically

### Secret Management

1. **Use environment secrets for production:** Provides additional protection and audit logging
2. **Enable required reviewers:** Prevents unauthorized production deployments
3. **Limit secret access:** Use branch protection and environment restrictions
4. **Never log secrets:** The workflow is designed to avoid exposing secrets in logs

### Server Hardening

1. **Dedicated deploy user:**
   ```bash
   sudo useradd -m -s /bin/bash deploy
   sudo usermod -aG docker deploy  # If using Docker
   ```

2. **Restricted sudo access:**
   ```bash
   # /etc/sudoers.d/deploy
   deploy ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/docker-compose
   ```

3. **Firewall rules:** Limit SSH access to GitHub Actions IP ranges

---

## Complete Configuration Checklist

### Repository Secrets (Settings > Secrets and variables > Actions)

| Secret Name | Required | Description |
|-------------|----------|-------------|
| `DEPLOY_SSH_KEY` | Yes | SSH private key for deployment |
| `STAGING_HOST` | Yes* | Staging server hostname/IP |
| `PRODUCTION_HOST` | Yes* | Production server hostname/IP |
| `DEPLOY_USER` | No | SSH username (defaults to `deploy`) |

*Can be environment-specific secrets instead

### Environment Variables

| Environment | Variable Name | Required | Description |
|-------------|--------------|----------|-------------|
| staging | `STAGING_URL` | Yes | Staging health check URL |
| production | `PRODUCTION_URL` | Yes | Production health check URL |

---

## Testing the Configuration

### 1. Verify Secret Presence

Run the workflow manually to check secret detection:

1. Go to **Actions** > **Deploy** workflow
2. Click **Run workflow**
3. Select **staging** environment
4. Click **Run workflow**
5. Check the "Verify required secrets" step for warnings

### 2. Test SSH Connectivity

From a local machine with the deploy key:

```bash
# Test staging connection
ssh -i deploy_key -o StrictHostKeyChecking=no deploy@staging.example.com echo "Connection successful"

# Test production connection
ssh -i deploy_key -o StrictHostKeyChecking=no deploy@app.example.com echo "Connection successful"
```

### 3. Verify Server Permissions

On the deployment server:

```bash
# Check deploy user can access required directories
sudo -u deploy ls -la /opt/dashboard/

# Check Docker permissions
sudo -u deploy docker ps

# Check docker-compose access
sudo -u deploy docker-compose -f /opt/dashboard/docker-compose.prod.yml config
```

### 4. Dry-Run Deployment

The workflow supports dry-run mode when hosts are not configured:

1. Configure only `DEPLOY_SSH_KEY` initially
2. Run the workflow - it will show what would be deployed without actually deploying
3. Verify the image tags and workflow steps
4. Add host secrets when ready for actual deployment

---

## Troubleshooting

### "Permission denied (publickey)"

1. Verify the public key is in `~/.ssh/authorized_keys` on the server
2. Check file permissions: `chmod 600 ~/.ssh/authorized_keys`
3. Verify the secret contains the complete private key
4. Ensure no extra whitespace in the secret value

### "Host key verification failed"

The workflow uses `ssh-keyscan` to automatically add host keys. If this fails:

1. Check the server is reachable from GitHub Actions
2. Verify the hostname/IP is correct
3. Manually add the host key to known_hosts if needed

### "STAGING_HOST not configured" Warning

This appears when the host secret is missing. Either:
1. Add the missing secret
2. If intentional (dry-run mode), ignore the warning

### Health Check Failures

1. Verify the URL variables are correct
2. Check the server is accessible from the internet
3. Verify the health endpoints exist:
   - Frontend: `$URL/`
   - Backend: `$URL/api/v1/health`
   - Monitoring: `$URL/api/v1/monitoring/health/live`

---

## Example Values Summary

```yaml
# Repository Secrets
DEPLOY_SSH_KEY: |
  -----BEGIN OPENSSH PRIVATE KEY-----
  b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
  QyNTUxOQAAACBxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxAAAA...
  -----END OPENSSH PRIVATE KEY-----

STAGING_HOST: staging.example.com
PRODUCTION_HOST: app.example.com
DEPLOY_USER: deploy  # Optional, defaults to 'deploy'

# Environment Variables
# staging environment:
STAGING_URL: https://staging.example.com

# production environment:
PRODUCTION_URL: https://app.example.com
```

---

## Related Documentation

- [Deployment Architecture](./DEPLOYMENT.md)
- [Docker Configuration](../docker/README.md)
- [GitHub Actions Workflow](.github/workflows/deploy.yml)
- [GitHub Encrypted Secrets Documentation](https://docs.github.com/en/actions/security-guides/encrypted-secrets)
