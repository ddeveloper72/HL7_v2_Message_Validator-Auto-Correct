# Docker Deployment Guide
## HL7 v2 Message Validator

This guide walks through building, running, and deploying the HL7 Validator application using Docker.

---

## 📋 Prerequisites

### Required Software
- **Docker Desktop** (Windows/Mac) or **Docker Engine** (Linux)
  - Download: https://www.docker.com/products/docker-desktop
  - Minimum version: 20.10+
- **Docker Compose** (included with Docker Desktop)
  - Minimum version: 2.0+

### Required Credentials
1. **Azure SQL Database** (already configured)
   - Server, database name, username, password
2. **Azure AD Application** (already configured)
   - Client ID, Client Secret, Tenant ID
3. **Gazelle API Key** (already configured)
   - Valid API key with expiration dates

---

## 🚀 Quick Start

### 1. Verify Environment Variables

Ensure your `.env` file contains all required variables:

```bash
# Application Mode
APP_MODE=production
ENVIRONMENT=docker

# Azure SQL Database
AZURE_SQL_SERVER=myfreesqldbserver72.database.windows.net
AZURE_SQL_DATABASE=gazelle-healthlink
AZURE_SQL_USERNAME=developer
AZURE_SQL_PASSWORD=your-password
DB_DRIVER=FreeTDS

# Security Keys (MUST be set for Docker)
SESSION_SECRET_KEY=your-64-character-hex-string
ENCRYPTION_KEY=your-fernet-key

# Azure AD
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback

# Gazelle API
GAZELLE_BASE_URL=https://testing.ehealthireland.ie
GAZELLE_API_KEY=your-api-key
GAZELLE_API_KEY_VALID_FROM=2026-05-20
GAZELLE_API_KEY_VALID_TO=2026-06-18
VERIFY_SSL=true
```

### 2. Generate Security Keys (if needed)

If `SESSION_SECRET_KEY` or `ENCRYPTION_KEY` are missing:

```powershell
# Generate SESSION_SECRET_KEY (64-character hex string)
python -c "import secrets; print('SESSION_SECRET_KEY=' + secrets.token_hex(32))"

# Generate ENCRYPTION_KEY (Fernet key)
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"
```

Add these to your `.env` file.

### 3. Build Docker Image

```powershell
# Build the image (takes 2-3 minutes first time)
docker-compose build
```

Expected output:
```
[+] Building 120.5s (15/15) FINISHED
 => [internal] load build definition
 => [internal] load .dockerignore
 => [internal] load metadata
 ...
 => => naming to docker.io/library/hl7_v2_message_validator-auto-correct-web
```

### 4. Run Application

```powershell
# Start in foreground (see logs)
docker-compose up

# OR start in background (detached mode)
docker-compose up -d
```

### 5. Access Application

Open browser to: **http://localhost:5000**

You should see the landing page. Click "Sign In with Microsoft" to authenticate.

### 6. Health Check

Test the health endpoint:
```powershell
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "app_mode": "production",
  "azure_ad_enabled": true,
  "database_enabled": true,
  "database": "connected",
  "timestamp": "2026-05-20T10:30:00"
}
```

---

## 🛠️ Common Commands

### Container Management

```powershell
# View running containers
docker-compose ps

# View logs (follow mode)
docker-compose logs -f

# View logs for specific service
docker-compose logs -f web

# Stop application
docker-compose down

# Stop and remove volumes (careful - deletes data!)
docker-compose down -v

# Restart application
docker-compose restart

# Restart specific service
docker-compose restart web
```

### Image Management

```powershell
# List images
docker images

# Remove unused images
docker image prune

# Rebuild from scratch (no cache)
docker-compose build --no-cache

# View image size
docker images hl7_v2_message_validator-auto-correct-web
```

### Debugging

```powershell
# Shell into running container
docker-compose exec web bash

# Check Python version
docker-compose exec web python --version

# Check installed packages
docker-compose exec web pip list

# Test database connection
docker-compose exec web python -c "import pyodbc; print(pyodbc.drivers())"

# View environment variables
docker-compose exec web env | grep AZURE
```

---

## 📊 Architecture

### Container Structure
```
hl7-validator (container)
├── Python 3.12 runtime
├── FreeTDS + ODBC drivers (Azure SQL)
├── Flask application
├── Gunicorn WSGI server (2 workers)
└── Volumes (persistent storage)
    ├── /app/uploads      → ./uploads
    ├── /app/processed    → ./processed
    └── /app/flask_session → ./flask_session
```

### Network
- **Bridge network:** `hl7-network`
- **External port:** 5000 (mapped to container port 5000)
- **Internal DNS:** Service name `web` resolves within network

### Health Checks
- **Interval:** Every 30 seconds
- **Timeout:** 10 seconds
- **Retries:** 3 attempts before marking unhealthy
- **Start period:** 40 seconds grace period for startup

---

## 🔧 Configuration

### Environment Variables Priority
1. Docker Compose `environment:` section (highest)
2. `.env` file via `env_file:`
3. Dockerfile `ENV` directives
4. Application defaults (lowest)

### Persistent Storage

Data is stored in mounted volumes:

```yaml
volumes:
  - ./uploads:/app/uploads          # Uploaded HL7 files
  - ./processed:/app/processed      # Processed files
  - ./flask_session:/app/flask_session  # User sessions
```

**Important:** These directories must be backed up separately!

### Database Connection

The application connects to Azure SQL Database using:
- **Driver:** FreeTDS (installed in container)
- **Path:** `/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so`
- **Protocol:** TDS 8.0 with encryption
- **Timeout:** 60 seconds for both connection and login

---

## 🚨 Troubleshooting

### Issue: Container Fails to Start

**Check logs:**
```powershell
docker-compose logs web
```

**Common causes:**
1. Missing environment variable → Check `.env` file
2. Port 5000 already in use → Change port in `docker-compose.yml`
3. Azure SQL firewall blocking Docker host IP

### Issue: Database Connection Timeout

**Symptoms:**
```
pyodbc.OperationalError: ('08001', 'TCP Provider: Timeout error [258]')
```

**Solutions:**
1. Add Docker host IP to Azure SQL firewall:
   - Get your public IP: `curl https://api.ipify.org`
   - Add to Azure Portal → SQL Database → Networking → Firewall rules

2. Enable "Allow Azure services":
   - Azure Portal → SQL Database → Networking
   - Toggle "Allow Azure services and resources to access this server"

3. Verify connection from container:
   ```powershell
   docker-compose exec web python diagnose_azure_sql.py
   ```

### Issue: Health Check Failing

**Check health status:**
```powershell
docker ps
```

Look for "(unhealthy)" in STATUS column.

**Diagnose:**
```powershell
# View detailed health check logs
docker inspect hl7-validator | grep -A 10 Health

# Test health endpoint manually
docker-compose exec web curl http://localhost:5000/health
```

### Issue: Sessions Not Persisting

**Symptoms:** User logged out after container restart

**Solution:** Verify `flask_session` volume is mounted:
```powershell
docker-compose exec web ls -la /app/flask_session
```

Should show session files. If empty, check `.env` has `SESSION_SECRET_KEY` set.

### Issue: PDF Export Not Working

**Check ReportLab:**
```powershell
docker-compose exec web python -c "from reportlab.lib.pagesizes import A4; print('ReportLab OK')"
```

If error, rebuild image to ensure `requirements.txt` was installed correctly.

---

## 🔒 Security Best Practices

### 1. Never Commit Secrets
- ✅ `.env` is in `.gitignore`
- ✅ `.dockerignore` excludes `.env`
- ❌ Never commit `.env` to version control

### 2. Use Docker Secrets (Production)

For production deployment to Docker Swarm or Kubernetes:

```yaml
# docker-compose.prod.yml
services:
  web:
    secrets:
      - session_secret
      - db_password
secrets:
  session_secret:
    external: true
  db_password:
    external: true
```

### 3. Run as Non-Root User
- ✅ Dockerfile already creates `appuser` (UID 1000)
- ✅ Container runs as `appuser`, not `root`

### 4. Regular Updates
```powershell
# Update base image
docker pull python:3.12-slim

# Rebuild with latest dependencies
docker-compose build --no-cache --pull
```

---

## 🌐 Production Deployment

### Option 1: Azure Container Apps (Recommended)

```bash
# Install Azure CLI
az login

# Create resource group
az group create --name hl7-validator-rg --location eastus

# Create container registry
az acr create --resource-group hl7-validator-rg \
  --name hl7validatoracr --sku Basic

# Build and push image
docker tag hl7_v2_message_validator-auto-correct-web hl7validatoracr.azurecr.io/hl7-validator:latest
az acr login --name hl7validatoracr
docker push hl7validatoracr.azurecr.io/hl7-validator:latest

# Deploy to Container Apps
az containerapp create \
  --name hl7-validator \
  --resource-group hl7-validator-rg \
  --image hl7validatoracr.azurecr.io/hl7-validator:latest \
  --target-port 5000 \
  --ingress external \
  --env-vars \
    APP_MODE=production \
    AZURE_SQL_SERVER=... \
    SESSION_SECRET_KEY=...
```

### Option 2: Azure Web App for Containers

1. **Azure Portal:**
   - Create new Web App
   - Select "Container" for publish
   - Choose "Docker Compose"
   - Upload `docker-compose.yml`

2. **Configure environment variables in App Settings**

3. **Enable Application Insights for monitoring**

### Option 3: Docker Swarm / Kubernetes

See separate deployment guides for orchestration platforms.

---

## 📈 Monitoring

### Container Stats

```powershell
# Real-time stats
docker stats hl7-validator

# Expected usage:
# CPU: 5-15% (idle), 50-80% (processing)
# Memory: 150-300 MB
# Network: Varies based on upload size
```

### Application Logs

```powershell
# Follow logs
docker-compose logs -f web

# Save logs to file
docker-compose logs web > logs.txt

# Filter for errors
docker-compose logs web | grep ERROR
```

### Health Monitoring

Set up automated health checks:
```bash
# Cron job example (Linux)
*/5 * * * * curl -f http://localhost:5000/health || alert_team
```

---

## 🔄 Updates and Maintenance

### Updating Application Code

```powershell
# 1. Stop container
docker-compose down

# 2. Pull latest code
git pull origin main

# 3. Rebuild image
docker-compose build

# 4. Start with new image
docker-compose up -d
```

### Database Schema Updates

```powershell
# Run migration script in container
docker-compose exec web python apply_schema_update.py
```

### Backup Strategy

**Volumes:**
```powershell
# Backup uploads and processed files
tar -czf backup-$(date +%Y%m%d).tar.gz uploads/ processed/ flask_session/
```

**Database:**
- Azure SQL has automatic backups (Point-in-Time Restore)
- Consider Azure Backup for additional protection

---

## 📝 Additional Resources

- **Docker Documentation:** https://docs.docker.com/
- **Azure Container Apps:** https://learn.microsoft.com/en-us/azure/container-apps/
- **Flask in Docker:** https://flask.palletsprojects.com/en/3.0.x/deploying/
- **FreeTDS Documentation:** https://www.freetds.org/

---

## 🆘 Support

If you encounter issues not covered in this guide:

1. Check container logs: `docker-compose logs -f`
2. Run diagnostics: `docker-compose exec web python diagnose_azure_sql.py`
3. Verify environment: `docker-compose exec web env`
4. Test health endpoint: `curl http://localhost:5000/health`

For application-specific issues, refer to `README.md` and project documentation.
