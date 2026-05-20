# Local Development Guide

## Application Modes

The application supports two modes controlled by the `APP_MODE` environment variable in `.env`:

### 🧪 Local Development Mode (Current)
```env
APP_MODE=local
```

**Features:**
- ✅ No Azure AD authentication (auto-login as "Local Developer")
- ✅ No database required (in-memory sessions only)
- ✅ No HTTPS required
- ✅ Fast startup, no external dependencies
- ✅ Perfect for testing validation and auto-correction features

**User Info:**
- Email: `local.dev@localhost`
- Name: `Local Developer`
- Session: Auto-created on first access

---

### 🚀 Production Mode
```env
APP_MODE=production
```

**Features:**
- ✅ Full Azure AD authentication (Microsoft login)
- ✅ Azure SQL Database integration
- ✅ Encrypted API key storage in database
- ✅ User validation history tracking
- ✅ Rate limiting enabled
- ✅ Security headers enforced

**Required Environment Variables:**
```env
# Azure AD
AZURE_AD_CLIENT_ID=your-client-id
AZURE_AD_CLIENT_SECRET=your-client-secret
AZURE_AD_TENANT_ID=your-tenant-id
AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback

# Azure SQL Database
AZURE_SQL_SERVER=your-server.database.windows.net
AZURE_SQL_DATABASE=your-database
AZURE_SQL_USERNAME=your-username
AZURE_SQL_PASSWORD=your-password
DB_DRIVER=ODBC Driver 18 for SQL Server

# Security
ENCRYPTION_KEY=your-fernet-encryption-key
SESSION_SECRET_KEY=your-session-secret
```

---

## Switching Modes

### 1. Switch to Production Mode
```powershell
# Update .env file
(Get-Content .env) -replace 'APP_MODE=local', 'APP_MODE=production' | Set-Content .env

# Restart Flask
python dashboard_app.py
```

### 2. Switch to Local Mode
```powershell
# Update .env file
(Get-Content .env) -replace 'APP_MODE=production', 'APP_MODE=local' | Set-Content .env

# Restart Flask
python dashboard_app.py
```

---

## Running the Application

### Start Flask Development Server
```bash
# Activate venv
.venv\Scripts\activate.bat

# Run app
python dashboard_app.py
```

**Access:** http://127.0.0.1:5000

### With Gunicorn (Production-like)
```bash
gunicorn dashboard_app:app --bind 0.0.0.0:5000 --timeout 120 --workers 2
```

---

## Testing Different Configurations

### Test Local Mode Features
1. File upload and validation
2. Auto-correction
3. PDF export (ReportLab)
4. Session persistence (file-based)
5. No authentication required

### Test Production Mode Features
1. Azure AD login flow
2. Database connection
3. API key encryption/storage
4. User validation history
5. Rate limiting
6. Security headers

---

## Troubleshooting

### Database Connection Issues (Production Mode)
```powershell
# Test database connectivity
python -c "from db_utils import DatabaseManager; db = DatabaseManager(); conn = db.get_connection(); print('✓ Database connected!'); conn.close()"
```

### ODBC Driver Issues
- Windows: Install [ODBC Driver 18 for SQL Server](https://go.microsoft.com/fwlink/?linkid=2249004)
- Verify: Run `odbcad32.exe` → Check "Drivers" tab

### Azure AD Issues (Production Mode)
- Verify redirect URI in Azure Portal matches `AZURE_AD_REDIRECT_URI`
- Check client secret hasn't expired
- Ensure app has `User.Read` permission

---

## Current Configuration

✅ **Mode:** LOCAL
✅ **Database:** In-Memory Only
✅ **Auth:** Auto-Login (No Azure AD)
✅ **PDF:** ReportLab (Working)
✅ **Dependencies:** All installed

**Quick Check:**
```bash
python dashboard_app.py
# Look for startup message:
# 🔧 Application Mode: LOCAL
#    - Azure AD Auth: DISABLED (Local Dev)
#    - Database: In-Memory Only
```

---

## Docker Deployment (Next Steps)

Both modes will work in Docker:
- **Local Mode:** Lightweight testing container
- **Production Mode:** Full Azure integration

See `DOCKER_READINESS_ANALYSIS.md` for details.
