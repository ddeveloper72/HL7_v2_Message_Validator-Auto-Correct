# Docker Mode Configuration - Issue Resolved

## Problem Statement

When running the application in Docker, attempting to use Azure AD authentication resulted in the app behaving like it was in local development mode instead of production mode.

## Root Cause

The `AZURE_AD_REDIRECT_URI` was **hardcoded** in `docker-compose.yml`:
```yaml
- AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback  # Hardcoded!
```

This prevented users from customizing the redirect URI and caused authentication issues. Additionally, there was no clear documentation about mode switching.

## Solution Implemented

### 1. Fixed docker-compose.yml
**Changed:** Made `AZURE_AD_REDIRECT_URI` pull from `.env` file:
```yaml
- AZURE_AD_REDIRECT_URI=${AZURE_AD_REDIRECT_URI:-http://localhost:5000/auth/callback}
```

**Changed:** Made `APP_MODE` configurable with default:
```yaml
- APP_MODE=${APP_MODE:-local}
```

**Added:** Comprehensive inline documentation explaining:
- How to register Azure AD app
- What each environment variable does
- Which variables are required for each mode

### 2. Created .env.docker.example
A complete example environment file showing:
- All available configuration options
- Step-by-step setup instructions for Azure AD
- Step-by-step setup instructions for Azure SQL
- Quick start guides for both local and production modes
- Commands to generate security keys

### 3. Created DOCKER_CONFIGURATION.md
A comprehensive configuration guide with:
- **Two deployment paths:** Local (5 min) vs Production (30 min)
- **Detailed Azure setup steps** with screenshots references
- **Troubleshooting section** for common issues
- **Mode switching instructions**
- **Production deployment guidance**
- **Complete environment variables reference table**

### 4. Updated Default Configuration
Changed `.env` default from `APP_MODE=production` to `APP_MODE=local` so:
- Users can test immediately with just a Gazelle API key
- No Azure setup required for initial testing
- Can upgrade to production mode when ready

## How It Works Now

### For Users Without Azure (Local Mode)

**What they need:**
- Just a Gazelle API key (free)

**Steps:**
1. Copy `.env.docker.example` to `.env`
2. Set `APP_MODE=local`
3. Add `GAZELLE_API_KEY`
4. Generate `SESSION_SECRET_KEY`
5. Run `docker-compose up -d`

**What works:**
- ✅ Full HL7 validation
- ✅ Auto-correction
- ✅ PDF reports
- ✅ All features except user auth and history

**Container logs show:**
```
🔧 Application Mode: LOCAL
   - Azure AD Auth: DISABLED (Local Dev)
   - Database: In-Memory Only
```

### For Users With Azure (Production Mode)

**What they need:**
- Azure AD app registration
- Azure SQL Database
- Gazelle API key

**Steps:**
1. Register app in Azure AD (detailed in DOCKER_CONFIGURATION.md)
2. Create Azure SQL Database
3. Copy `.env.docker.example` to `.env`
4. Set `APP_MODE=production`
5. Configure all `AZURE_*` variables
6. Generate security keys
7. Run `docker-compose up -d`

**What works:**
- ✅ Everything from local mode, plus:
- ✅ Azure AD authentication (SSO)
- ✅ Multi-user support
- ✅ Validation history per user
- ✅ Encrypted API key storage
- ✅ Audit trails

**Container logs show:**
```
🔧 Application Mode: PRODUCTION
   - Azure AD Auth: ENABLED
   - Database: Azure SQL
```

## Testing Results

### Local Mode Test
```bash
$ curl http://localhost:5000/health
{
  "app_mode": "local",
  "azure_ad_enabled": false,
  "database_enabled": false,
  "status": "healthy",
  "timestamp": "2026-05-20T18:29:20Z"
}
```
✅ Status: 200 OK

### Production Mode Test
```bash
$ curl http://localhost:5000/health
{
  "app_mode": "production",
  "azure_ad_enabled": true,
  "database": "connected",
  "database_enabled": true,
  "status": "healthy",
  "timestamp": "2026-05-20T18:15:50Z"
}
```
✅ Status: 200 OK

## Files Modified/Created

### Modified
1. **docker-compose.yml**
   - Made all Azure variables dynamic (pull from .env)
   - Added comprehensive inline documentation
   - Made APP_MODE easily switchable
   - Added default values for optional variables

2. **.env**
   - Changed default to `APP_MODE=local`
   - Added clarifying comments

### Created
1. **.env.docker.example**
   - Complete example configuration
   - Step-by-step Azure setup instructions
   - Command-line helpers for key generation

2. **DOCKER_CONFIGURATION.md**
   - User-friendly configuration guide
   - Two clear deployment paths
   - Troubleshooting section
   - Environment variables reference table

3. **DOCKER_MODE.md** (this file)
   - Technical explanation of the issue
   - Solution details
   - Testing results

## How Users Should Configure

### New Users (Recommended Path)

1. **Start with local mode:**
   ```bash
   cp .env.docker.example .env
   # Edit .env, set APP_MODE=local, add GAZELLE_API_KEY
   docker-compose up -d
   ```

2. **Test the application** - validate some files, try features

3. **Upgrade to production when needed:**
   - Follow [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md) production setup
   - Change `APP_MODE=production` in .env
   - Add Azure credentials
   - Restart: `docker-compose restart`

### Enterprise Users (Direct to Production)

Follow the "Production Mode" section in [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md):
1. Register Azure AD app (10 min)
2. Create Azure SQL Database (15 min)
3. Configure .env file (5 min)
4. Deploy: `docker-compose up -d`

## Switching Between Modes

**Local → Production:**
```bash
# Edit .env
APP_MODE=production
# Add all AZURE_* variables

# Restart
docker-compose restart
```

**Production → Local:**
```bash
# Edit .env
APP_MODE=local
# Azure variables can stay but will be ignored

# Restart
docker-compose restart
```

## Documentation Flow

```
User starts here
      ↓
DOCKER_QUICK_START.md (2 min read)
      ↓
DOCKER_CONFIGURATION.md (choose mode)
      ↓
    ├─→ Local Mode (5 min setup)
    │   └─→ Start validating immediately
    │
    └─→ Production Mode (30 min setup)
        ├─→ Azure AD registration
        ├─→ Azure SQL setup
        └─→ Full enterprise deployment
```

## Success Criteria - All Met ✅

- ✅ Users can run Docker without any Azure setup
- ✅ Users can upgrade to production mode when ready
- ✅ All configuration is in .env file (not hardcoded)
- ✅ Clear documentation for both modes
- ✅ Troubleshooting guide for common issues
- ✅ Container works in both modes
- ✅ Health endpoint reports correct mode
- ✅ Easy mode switching

## Next Steps for End Users

1. **Read:** [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md)
2. **Copy:** `.env.docker.example` → `.env`
3. **Choose:** Local or Production mode
4. **Run:** `docker-compose up -d`
5. **Open:** http://localhost:5000

---

**Issue:** Resolved ✅  
**Tested:** Both local and production modes working  
**Documentation:** Complete  
**Date:** May 20, 2026
