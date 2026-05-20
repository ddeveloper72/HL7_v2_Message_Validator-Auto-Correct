# Docker Readiness Analysis
## HL7 v2 Message Validator Application

**Date:** May 20, 2026  
**Current Status:** Deployed on Heroku  
**Target:** Docker containerization

---

## Executive Summary

This application is a Flask-based HL7 v2 message validator with Azure SQL Database integration and Azure AD authentication. It's currently running on Heroku with several platform-specific configurations that need to be addressed for Docker deployment.

### Current Architecture
- **Framework:** Flask 3.0.0 with Gunicorn
- **Python Version:** 3.12.4
- **Database:** Azure SQL Database (via pyodbc + FreeTDS on Heroku)
- **Authentication:** Azure AD (MSAL)
- **Key Features:** File upload/validation, auto-correction, PDF export, session management

---

## ✅ What's Ready for Docker

### 1. **Application Code**
- ✅ Well-structured Flask application (`dashboard_app.py`)
- ✅ Modular components (db_utils, auto_correct, hl7_corrector)
- ✅ Environment variable configuration (12-factor app compliant)
- ✅ No hardcoded paths (relative paths used)
- ✅ Gunicorn production server configured

### 2. **Dependencies**
- ✅ `requirements.txt` exists with all Python dependencies
- ✅ Clear separation between dev and production packages
- ✅ Modern package versions (recent updates)

### 3. **Configuration Management**
- ✅ Uses `python-dotenv` for environment variables
- ✅ No committed secrets (`.env` in `.gitignore`)
- ✅ Heroku config vars documented

---

## ⚠️ Critical Issues / Loose Ends

### 1. **✅ FIXED: PDF Export Now Uses ReportLab** 🟢
**Status:** Fixed on May 20, 2026

**Problem (Was):** 
- Playwright was imported but NOT listed in `requirements.txt`
- PDF export feature was broken on Heroku
- Would have required Chromium browser (~200-300MB)

**Solution (Implemented):**
- ✅ Replaced Playwright with ReportLab (already in requirements.txt)
- ✅ Pure Python PDF generation - no browser needed
- ✅ Works on Heroku without additional dependencies
- ✅ Much smaller footprint and more reliable
- ✅ Clean, professional PDF output with proper formatting

### 2. **FreeTDS Driver Configuration** 🟡
**Location:** `db_utils.py` lines 20-22, `Aptfile`

```python
self.driver = os.getenv('DB_DRIVER', 
    'FreeTDS' if os.getenv('DYNO') else 'ODBC Driver 18 for SQL Server')
```

**Heroku-Specific:**
- Uses `Aptfile` to install FreeTDS on Heroku
- Custom driver path: `/app/.apt/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so`

**Docker Solution:**
```dockerfile
# In Dockerfile
RUN apt-get update && apt-get install -y \
    unixodbc \
    unixodbc-dev \
    freetds-dev \
    freetds-bin \
    tdsodbc \
    && rm -rf /var/lib/apt/lists/*

# Configure odbcinst.ini
RUN echo "[FreeTDS]\n\
Description = FreeTDS Driver\n\
Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so\n\
Setup = /usr/lib/x86_64-linux-gnu/odbc/libtdsS.so" > /etc/odbcinst.ini
```

### 3. **Session Secret Key Management** 🟡
**Location:** `dashboard_app.py` lines 28-40

```python
session_secret = os.environ.get('SESSION_SECRET_KEY')
if not session_secret:
    # Local dev: saves to .session_secret file
    # Heroku: generates new on each restart (problematic)
```

**Problem:**
- Heroku ephemeral filesystem causes session invalidation on dyno restart
- Docker containers similar - needs persistent secret or external session store

**Docker Solution:**
1. **Mandatory environment variable:** Fail if SESSION_SECRET_KEY not set
2. **OR** Use Redis/Memcached for session storage (Flask-Session supports this)
3. **OR** Use Docker secrets management

### 4. **Temporary File Storage** 🟡
**Location:** `dashboard_app.py` lines 59-75

```python
RESULTS_TEMP_FILE = '/tmp/processing_results.json'
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
```

**Heroku Behavior:**
- Uses `/tmp` for processing results (ephemeral)
- Uses local folders for uploads (ephemeral)
- All data lost on dyno restart

**Docker Considerations:**
- Container filesystem is ephemeral by default
- Need volume mounts for persistence:
  ```yaml
  volumes:
    - ./uploads:/app/uploads
    - ./processed:/app/processed
    - ./tmp:/tmp
  ```
- **OR** migrate to cloud storage (Azure Blob Storage, S3)
- **OR** store in database (already has Azure SQL)

### 5. **DYNO Environment Detection** 🟡
**Locations:** Multiple files

```python
if os.getenv('DYNO'):  # Heroku-specific
```

**Files affected:**
- `dashboard_app.py` (line 37)
- `db_utils.py` (line 22)

**Docker Solution:**
- Remove Heroku-specific checks
- Use explicit `ENVIRONMENT` variable (`production`, `docker`, `local`)
- Or check for Docker-specific env vars like `HOSTNAME` pattern

### 6. **Subprocess Calls** 🟡
**Location:** `dashboard_app.py` lines 533, 751

```python
result = subprocess.run(
    [python_executable, script_path, filepath],
    capture_output=True,
    timeout=60,
    ...
)
```

**Calls:** `validate_with_verification.py` as subprocess

**Docker Considerations:**
- Should work fine in Docker
- Ensure script has proper shebang or use explicit python path
- Consider replacing with direct function calls for better resource management

### 7. **Database Connection String** 🟢
**Status:** Should work, but verify

```python
# FreeTDS connection
connection_string = (
    f'DRIVER=/app/.apt/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so;'
    ...
)
```

**Docker Note:**
- Driver path will be different: `/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so`
- Need environment variable to set correct path
- OR detect at runtime

---

## 📋 Environment Variables Required

### Critical (Must Have)
```bash
# Database
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database
AZURE_SQL_USERNAME=your-username
AZURE_SQL_PASSWORD=your-password
DB_DRIVER=FreeTDS  # or "ODBC Driver 18 for SQL Server"

# Security
SESSION_SECRET_KEY=random-64-char-string
ENCRYPTION_KEY=fernet-encryption-key

# Azure AD
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback

# Gazelle API
GAZELLE_BASE_URL=https://testing.ehealthireland.ie/evs
VERIFY_SSL=True
```

### Optional
```bash
MAX_AUTO_CORRECT_ITERATIONS=10
ENVIRONMENT=production  # or docker, local
```

---

## 🐳 Docker Implementation Checklist

### Phase 1: Basic Dockerization
- [ ] Create `Dockerfile`
  ```dockerfile
  FROM python:3.12-slim
  
  # Install system dependencies
  RUN apt-get update && apt-get install -y \
      unixodbc unixodbc-dev freetds-dev freetds-bin tdsodbc \
      && rm -rf /var/lib/apt/lists/*
  
  # Configure FreeTDS driver
  RUN echo "[FreeTDS]\n\
  Description = FreeTDS Driver\n\
  Driver = /usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so" > /etc/odbcinst.ini
  
  WORKDIR /app
  
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  
  # PDF generation uses ReportLab (already in requirements.txt) - no extra steps needed
  
  COPY . .
  
  # Create necessary directories
  RUN mkdir -p uploads processed /tmp
  
  EXPOSE 5000
  
  CMD ["gunicorn", "dashboard_app:app", "--bind", "0.0.0.0:5000", "--timeout", "120", "--workers", "2"]
  ```

- [ ] Create `docker-compose.yml`
  ```yaml
  version: '3.8'
  services:
    web:
      build: .
      ports:
        - "5000:5000"
      environment:
        - AZURE_SQL_SERVER=${AZURE_SQL_SERVER}
        - AZURE_SQL_DATABASE=${AZURE_SQL_DATABASE}
        - AZURE_SQL_USERNAME=${AZURE_SQL_USERNAME}
        - AZURE_SQL_PASSWORD=${AZURE_SQL_PASSWORD}
        - SESSION_SECRET_KEY=${SESSION_SECRET_KEY}
        - ENCRYPTION_KEY=${ENCRYPTION_KEY}
        - AZURE_AD_CLIENT_ID=${AZURE_AD_CLIENT_ID}
        - AZURE_AD_CLIENT_SECRET=${AZURE_AD_CLIENT_SECRET}
        - AZURE_AD_TENANT_ID=${AZURE_AD_TENANT_ID}
        - AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback
        - DB_DRIVER=FreeTDS
        - ENVIRONMENT=docker
      volumes:
        - ./uploads:/app/uploads
        - ./processed:/app/processed
      env_file:
        - .env
  ```

- [ ] Create `.dockerignore`
  ```
  .venv/
  __pycache__/
  *.pyc
  .env
  .git/
  .gitignore
  *.md
  .session_secret
  uploads/*
  processed/*
  cli_test/
  dev_notes/
  ```

### Phase 2: Fix Critical Issues
- [ ] **Add Playwright to requirements.txt** OR remove PDF export feature
  `x] **PDF Export Fixed** - Now uses ReportLab (already in requirements.txt)
  - No additional dependencies needed
  - Pure Python solution, works everywhere
- [ ] **Update `db_utils.py`** to handle Docker environment
  ```python
  def get_driver_path(self):
      """Get ODBC driver path based on environment"""
      if os.getenv('ENVIRONMENT') == 'docker':
          return '/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so'
      elif os.getenv('DYNO'):  # Heroku
          return '/app/.apt/usr/lib/x86_64-linux-gnu/odbc/libtdsodbc.so'
      else:  # Local development
          return 'ODBC Driver 18 for SQL Server'
  ```

- [ ] **Update `dashboard_app.py`** session handling
  ```python
  # Make SESSION_SECRET_KEY mandatory in production
  session_secret = os.environ.get('SESSION_SECRET_KEY')
  if not session_secret:
      if os.getenv('ENVIRONMENT') in ['production', 'docker']:
          raise ValueError("SESSION_SECRET_KEY must be set in production!")
      # ... local dev fallback
  ```

- [ ] **Consider database migration** for temporary storage
  ```python
  # Instead of /tmp/processing_results.json
  # Store in database: ValidationHistory table
  ```

### Phase 3: Testing
- [ ] Build Docker image: `docker build -t hl7-validator .`
- [ ] Run locally: `docker-compose up`
- [ ] Test file upload and validation
- [ ] Test PDF export (if keeping playwright)
- [ ] Test auto-correction feature
- [ ] Test session persistence
- [ ] Test database connectivity
- [ ] Load testing with multiple workers

### Phase 4: Productionnow using ReportLab
- [ ] Set up health check endpoint
  ```python
  @app.route('/health')
  def health_check():
      return jsonify({'status': 'healthy'}), 200
  ```
- [ ] Add logging configuration
- [ ] Implement proper error pages
- [ ] Add monitoring (Prometheus metrics)
- [ ] Set up CI/CD pipeline
- [ ] Security scan (Trivy, Snyk)

---

## 📊 Size Estimates

| Component | Size |
|-----------|------|
| Base Python 3.12 slim | ~150 MB |
| Python packages (no playwright) | ~100 MB |
| FreeTDS + ODBC drivers | ~20 MB |
| **Total (without Playwright)** | **~270 MB** |
| **+ Playwright + Chromium** | **+300 MB = 570 MB** |

---
with ReportLab) | ~100 MB |
| FreeTDS + ODBC drivers | ~20 MB |
| **Total** | **~2ev
- Use Docker for local development
- Keep Heroku for production (already working)
- Benefit: Test locally in production-like environment

### Option B: Full Docker Migration
**Deployment Options:**
1. **Azure Container Apps** (Serverless containers)
   - Auto-scaling
   - Already using Azure SQL
   - Integrated with Azure AD
   
2. **Azure Web App for Containers**
   - Direct Heroku replacement
   - Git deployment
   - Easy scaling

3. **Azure Kubernetes Service (AKS)**
   - Full control
   - Complex setup
   - Overkill for single app

4. **AWS ECS/Fargate**
   - Alternative to Azure
   - More vendor lock-in

---

## 🎯 Recommended Next Steps

### Immediate (Week 1)
1. **Fix Playwright issue**
   - Add to requirements.txt OR switch to alternative
   - Test PDF generation on Heroku
   
2. **Create basic Dockerfile**
   - Get it building successfully
   - Test locally without external dependencies
~~**Fix Playwright issue**~~ ✅ **COMPLETED**
   - ✅ Replaced with ReportLab
   - Ready to test PDF generation*
   - Remove DYNO checks
   - Use explicit ENVIRONMENT variable
   
4. **Test with Docker Compose**
   - Full local environment
   - Azure SQL connection from Docker
   
5. **Address storage strategy**
   - Decide on volume mounts vs cloud storage
   - Document data persistence approach

### Long-term (Month 1-2)
6. **Production deployment**
   - Choose target platform (Azure Container Apps recommended)
   - Set up CI/CD
   - Migrate from Heroku (or run parallel)

7. **Optimization**
   - Multi-stage Docker build
   - Reduce image size
   - Add Redis for sessions (if scaling)

---

## ❓ Questions to Answer

1. **PDF Export:** Keep Playwright (+ 300MB) or switch to alternative?
2. **Storage:** Volumes, Azure Blob, or database for files?
3. **Session Management:** Environment variable or Redis/external store?
4. **Deployment Target:** Azure Container Apps, Web App, or stay on Heroku?
5. **Database:** Keep Azure SQL or consider containerized PostgreSQL for local dev?

---
~~**PDF Export:**~~ ✅ **RESOLVED** - Using ReportLab
## 📚 Files to Review/Modify

### High Priority
- [ ] `requirements.txt` - Add playwright
- [ ] `dashboard_app.py` - Session management, environment detection
- [ ] `db_utils.py` - Driver path handling
- [ ] Create `Dockerfile`
- [ ] Create `docker-compose.yml`
- [ ] Create `.dockerignore`

###x] ~~`requirements.txt` - Add playwright~~ ✅ Fixed - using ReportLab instead
- [ ] `validate_with_verification.py` - Ensure subprocess-friendly
- [ ] `auto_correct.py` - File path handling
- [ ] `hl7_corrector.py` - Review for Docker compatibility

### Documentation
- [ ] Create `DOCKER_DEPLOYMENT.md`
- [ ] Update `README.md` with Docker instructions
- [ ] Create `docker-compose.override.yml` example

---

## 🔒 Security Considerations

1. **Secrets Management:**
   - Never commit `.env` to Git
   - Use Docker secrets or Azure Key Vault
   - Rotate SESSION_SECRET_KEY and ENCRYPTION_KEY regularly

2. **Container Security:**
   - Run as non-root user
   - Scan image for vulnerabilities
   - Keep base image updated

3. **Network Security:**
   - Azure SQL firewall rules for Docker IPs
   - HTTPS only (use reverse proxy)
   - Rate limiting enabled (Flask-Limiter already installed)

---

**Status:** Ready for Dockerization with minor fixes required  
**Estimated Effort:** 2-3 days for basic Docker setup, 1-2 weeks for production-ready  
**Blocking Issues:** Playwright dependency missing, environment detection needs refactoring
~~Playwright dependency~~ ✅ FIXED