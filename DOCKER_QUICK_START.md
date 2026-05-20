# Docker Implementation - Quick Reference

## ✅ What Was Implemented

### 1. Docker Configuration Files

| File | Purpose | Status |
|------|---------|--------|
| `Dockerfile` | Container image definition with Python 3.12, FreeTDS, and ODBC drivers | ✅ Created |
| `docker-compose.yml` | Multi-service orchestration with volumes and networks | ✅ Created |
| `.dockerignore` | Excludes unnecessary files from Docker build context | ✅ Created |
| `DOCKER_DEPLOYMENT.md` | Comprehensive deployment and troubleshooting guide | ✅ Created |

### 2. Code Updates

| File | Changes | Status |
|------|---------|--------|
| `db_utils.py` | Added Docker environment detection for FreeTDS driver path | ✅ Updated |
| `dashboard_app.py` | Added `/health` endpoint and stricter session key validation | ✅ Updated |
| `dashboard_app.py` | Improved session handling for Docker/production environments | ✅ Updated |

### 3. Directory Structure

```
├── Dockerfile                 # ✅ Multi-stage build with security best practices
├── docker-compose.yml         # ✅ Complete local development setup
├── .dockerignore             # ✅ Optimized build context
├── uploads/.gitkeep          # ✅ Persistent storage directory
├── processed/.gitkeep        # ✅ Persistent storage directory
└── flask_session/            # ✅ Session storage (created automatically)
```

---

## 🚀 Quick Start Commands

### First Time Setup

```powershell
# 1. Verify .env file has all required variables
cat .env

# 2. Generate security keys if missing
python -c "import secrets; print('SESSION_SECRET_KEY=' + secrets.token_hex(32))"

# 3. Build Docker image
docker-compose build

# 4. Start application
docker-compose up -d

# 5. Check health
curl http://localhost:5000/health
```

### Daily Usage

```powershell
# Start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart after code changes
docker-compose restart
```

---

## 🔍 Key Features

### 1. Multi-Environment Support
- ✅ **Local:** Uses ODBC Driver 18 for SQL Server
- ✅ **Docker:** Uses FreeTDS driver at `/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so`
- ✅ **Heroku:** Uses FreeTDS driver at `/app/.apt/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so`

Auto-detected via `ENVIRONMENT` variable or `DYNO` (Heroku) environment.

### 2. Health Check Endpoint

```http
GET /health HTTP/1.1
Host: localhost:5000
```

**Response:**
```json
{
  "status": "healthy",
  "app_mode": "production",
  "azure_ad_enabled": true,
  "database_enabled": true,
  "database": "connected",
  "timestamp": "2026-05-20T18:45:00"
}
```

**Container Health:**
- ✅ Checks every 30 seconds
- ✅ 3 retries before marking unhealthy
- ✅ 40-second startup grace period

### 3. Security Improvements

**Session Handling:**
- ✅ Requires `SESSION_SECRET_KEY` in production/Docker
- ✅ Fails fast if missing (prevents weak default keys)
- ✅ Auto-generates only for local development

**Container Security:**
- ✅ Runs as non-root user (`appuser`, UID 1000)
- ✅ Minimal base image (python:3.12-slim ~150MB)
- ✅ No unnecessary packages installed

### 4. Persistent Storage

**Volumes mounted:**
```yaml
./uploads:/app/uploads           # User-uploaded HL7 files
./processed:/app/processed       # Processed/corrected files
./flask_session:/app/flask_session  # User session data
```

**Data persists across:**
- ✅ Container restarts
- ✅ Image rebuilds
- ✅ Application updates

---

## 📊 Container Specifications

| Metric | Value |
|--------|-------|
| Base Image | `python:3.12-slim` |
| Estimated Size | ~270 MB |
| Port | 5000 |
| Workers | 2 (Gunicorn) |
| Timeout | 120 seconds |
| Memory (idle) | ~150-200 MB |
| Memory (active) | ~250-400 MB |

---

## 🧪 Testing Checklist

Before deploying to production:

- [ ] Build succeeds: `docker-compose build`
- [ ] Container starts: `docker-compose up -d`
- [ ] Health check passes: `curl http://localhost:5000/health`
- [ ] Can access landing page: http://localhost:5000
- [ ] Azure AD login works
- [ ] Database connection successful (check logs for connection messages)
- [ ] File upload works
- [ ] Validation with Gazelle API works
- [ ] Auto-correction works
- [ ] PDF export works
- [ ] Session persists after container restart
- [ ] API key saved to database correctly

---

## 🔧 Troubleshooting Quick Reference

### Container Won't Start

```powershell
# Check logs for error
docker-compose logs web

# Common issues:
# - Missing SESSION_SECRET_KEY in .env
# - Port 5000 already in use
# - Invalid .env syntax
```

### Database Connection Fails

```powershell
# Test from container
docker-compose exec web python diagnose_azure_sql.py

# Add Docker host IP to Azure SQL firewall
# Get your IP: curl https://api.ipify.org
```

### Health Check Failing

```powershell
# Check container status
docker ps

# View health logs
docker inspect hl7-validator | grep -A 10 Health

# Test manually
docker-compose exec web curl http://localhost:5000/health
```

---

## 📁 Environment Variables Reference

### Required (Must Set)

```bash
# Security
SESSION_SECRET_KEY=<64-char-hex-string>
ENCRYPTION_KEY=<fernet-key>

# Database
AZURE_SQL_SERVER=myfreesqldbserver72.database.windows.net
AZURE_SQL_DATABASE=gazelle-healthlink
AZURE_SQL_USERNAME=developer
AZURE_SQL_PASSWORD=<password>

# Azure AD
AZURE_AD_CLIENT_ID=<client-id>
AZURE_AD_CLIENT_SECRET=<client-secret>
AZURE_AD_TENANT_ID=<tenant-id>

# API
GAZELLE_API_KEY=<your-key>
```

### Auto-Detected

```bash
ENVIRONMENT=docker    # Auto-set by docker-compose
APP_MODE=production   # Controls features
DB_DRIVER=FreeTDS     # Driver for Azure SQL
```

---

## 🎯 Next Steps

### Immediate
1. ✅ Docker files created
2. ⏳ Test Docker build: `docker-compose build`
3. ⏳ Test Docker run: `docker-compose up`
4. ⏳ Verify health check: `/health` endpoint
5. ⏳ Test full authentication and validation flow

### Short Term
- Deploy to Azure Container Apps
- Set up CI/CD pipeline (GitHub Actions)
- Configure monitoring (Azure Application Insights)
- Load testing with multiple concurrent users

### Long Term
- Consider Redis for session storage (if scaling beyond 1 instance)
- Implement log aggregation (ELK stack or Azure Monitor)
- Add Prometheus metrics endpoint
- Container security scanning (Trivy, Snyk)

---

## 📚 Documentation

- **Full Deployment Guide:** [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- **Architecture Analysis:** [DOCKER_READINESS_ANALYSIS.md](DOCKER_READINESS_ANALYSIS.md)
- **Main README:** [README.md](README.md)
- **Azure Setup:** [AZURE_SETUP_GUIDE.md](AZURE_SETUP_GUIDE.md)

---

## ✨ Key Improvements Over Heroku

| Feature | Heroku | Docker | Benefit |
|---------|--------|--------|---------|
| **Startup** | Cold start delays | Instant (running container) | Better UX |
| **Cost** | $7-25/month | Azure free tier or pay-per-use | Lower cost |
| **Control** | Limited | Full container control | More flexibility |
| **Local Testing** | Different environment | Same as production | Fewer surprises |
| **Scaling** | Manual | Auto-scaling (Container Apps) | Better performance |
| **Monitoring** | Add-ons required | Built-in (Azure Monitor) | Easier debugging |

---

**Status:** ✅ Docker implementation complete and ready for testing!

**Last Updated:** May 20, 2026
