# Docker Configuration Guide

## Quick Start - Choose Your Mode

### Option 1: Local Mode (No Azure Required)
**Best for:** Quick testing, development, single-user validation

**What you need:**
- Just a Gazelle API key (free from https://testing.ehealthireland.ie)

**Setup (5 minutes):**
```bash
# 1. Copy example env file
cp .env.docker.example .env

# 2. Edit .env and set:
APP_MODE=local
GAZELLE_API_KEY=your_key_from_gazelle

# 3. Generate session key
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output to SESSION_SECRET_KEY in .env

# 4. Start Docker
docker-compose up -d

# 5. Open browser
http://localhost:5000
```

**Features available:**
- HL7 file validation
- Auto-correction
- PDF report generation
- Batch processing
- User authentication
- Validation history

---

### Option 2: Production Mode (Azure Integration)
**Best for:** Multi-user deployment, enterprise use, audit trails

**What you need:**
- Azure subscription (free tier works)
- Azure AD app registration
- Azure SQL Database

**Setup (30 minutes):**

#### Step 1: Azure AD App Registration
1. Go to https://portal.azure.com
2. Navigate to **Azure Active Directory** → **App registrations**
3. Click **New registration**
 - Name: `HL7 Message Validator`
 - Supported account types: `Accounts in this organizational directory only`
 - Redirect URI: `Web` → `http://localhost:5000/auth/callback`
4. Click **Register**
5. From the **Overview** page, copy:
 - **Application (client) ID** → `AZURE_AD_CLIENT_ID`
 - **Directory (tenant) ID** → `AZURE_AD_TENANT_ID`
6. Go to **Certificates & secrets** → **New client secret**
 - Description: `Docker deployment`
 - Expires: 24 months
 - Copy the **Value** (not ID) → `AZURE_AD_CLIENT_SECRET`

#### Step 2: Azure SQL Database
1. In Azure Portal, create a **SQL Database**
 - Resource group: Create new or use existing
 - Database name: `hl7-validator`
 - Server: Create new
 - Pricing tier: **Basic** (5 DTUs, $5/month) is sufficient
2. Configure **Firewall** (in SQL Server settings):
 - Add your IP address
 - Enable "Allow Azure services and resources to access this server"
3. Copy connection details:
 - **Server name** → `AZURE_SQL_SERVER`
 - **Database name** → `AZURE_SQL_DATABASE`
 - **Admin username** → `AZURE_SQL_USERNAME`
 - **Admin password** → `AZURE_SQL_PASSWORD`
4. Initialize database schema:
 ```bash
 # From your local machine (not Docker yet)
 python init_database.py
 ```

#### Step 3: Configure Environment
```bash
# 1. Copy example env file
cp .env.docker.example .env

# 2. Edit .env and set:
APP_MODE=production

# Gazelle API
GAZELLE_API_KEY=your_key_here

# Azure AD (from Step 1)
AZURE_AD_CLIENT_ID=7f9d82a7-xxx
AZURE_AD_CLIENT_SECRET=j878Q~xxx
AZURE_AD_TENANT_ID=fc6570ff-xxx
AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback

# Azure SQL (from Step 2)
AZURE_SQL_SERVER=yourserver.database.windows.net
AZURE_SQL_DATABASE=hl7-validator
AZURE_SQL_USERNAME=admin_user
AZURE_SQL_PASSWORD=your_password

# 3. Generate security keys
# Session key:
python -c "import secrets; print(secrets.token_hex(32))"
# Copy to SESSION_SECRET_KEY

# Encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Copy to ENCRYPTION_KEY

# 4. Start Docker
docker-compose up -d

# 5. Open browser and sign in
http://localhost:5000
```

**Features available:**
- HL7 file validation
- Auto-correction
- PDF report generation
- Batch processing
- Azure AD authentication (Single Sign-On)
- Validation history per user
- Encrypted API key storage
- Multi-user support
- Audit trails

---

## Troubleshooting

### "Sign in with Microsoft" redirects to local mode

**Cause:** `AZURE_AD_REDIRECT_URI` not properly configured

**Solution:**
1. Check your `.env` file has:
 ```bash
 AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback
 ```
2. Verify it matches **exactly** in Azure AD app registration:
 - Go to Azure Portal → Azure Active Directory → App registrations
 - Select your app → Authentication
 - Under "Web" platform, ensure redirect URI is: `http://localhost:5000/auth/callback`
3. Restart Docker:
 ```bash
 docker-compose restart
 ```

### Container won't start / health check failing

**Check logs:**
```bash
docker-compose logs -f web
```

**Common issues:**
1. **Database connection failed**
 - Verify firewall rules in Azure SQL allow your IP
 - Check connection string in .env
 - Test connectivity: `telnet yourserver.database.windows.net 1433`

2. **Missing environment variables**
 - Ensure SESSION_SECRET_KEY is set in .env
 - For production mode, verify all AZURE_* variables are set

3. **Invalid API key**
 - Verify GAZELLE_API_KEY is correct
 - Check key hasn't expired

### Azure AD login fails with "AADSTS50011"

**Cause:** Redirect URI mismatch

**Solution:**
1. The redirect URI in your Azure AD app **must exactly match** the one in .env
2. Common mistake: `http://localhost:5000/auth/callback` vs `http://localhost:5000/auth/callback/` (trailing slash)
3. After fixing, restart: `docker-compose restart`

### Database connection works locally but not in Docker

**Cause:** Azure SQL firewall blocking Docker container's IP

**Solution:**
1. In Azure Portal → SQL Server → Firewalls and virtual networks
2. Enable: "Allow Azure services and resources to access this server"
3. Or add rule: `0.0.0.0` to `0.0.0.0` (allows all) - **only for testing!**
4. For production, use specific IP ranges or VNet integration

---

## Switching Modes

### From Local → Production
1. Edit `.env`: Change `APP_MODE=local` to `APP_MODE=production`
2. Add all AZURE_* variables to .env (see "Production Mode" setup above)
3. Restart: `docker-compose restart`

### From Production → Local
1. Edit `.env`: Change `APP_MODE=production` to `APP_MODE=local`
2. Restart: `docker-compose restart`
3. Azure variables will be ignored but can stay in .env

---

## Deploying to Production Domain

When deploying to a public URL (e.g., `https://myapp.azurewebsites.net`):

### 1. Update Redirect URI
In `.env`:
```bash
AZURE_AD_REDIRECT_URI=https://myapp.azurewebsites.net/auth/callback
```

### 2. Update Azure AD App Registration
1. Go to Azure Portal → Azure Active Directory → App registrations
2. Select your app → Authentication
3. Add new redirect URI: `https://myapp.azurewebsites.net/auth/callback`
4. **Important:** You can have multiple redirect URIs (keep localhost for testing)

### 3. Update Azure SQL Firewall
1. Add your production server's IP address/range
2. Or use VNet integration for better security

### 4. Deploy
- **Azure Container Apps:** Use Azure CLI or Portal
- **Azure App Service:** Deploy via Docker Hub or ACR
- **Other:** Use your cloud provider's container service

See [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) for detailed deployment guides.

---

## Environment Variables Reference

| Variable | Required | Mode | Description |
|----------|----------|------|-------------|
| `APP_MODE` | Yes | All | `local` or `production` |
| `GAZELLE_API_KEY` | Yes | All | API key from Gazelle EVS |
| `SESSION_SECRET_KEY` | Yes | All | Flask session encryption |
| `AZURE_AD_CLIENT_ID` | Production only | Production | Azure AD app client ID |
| `AZURE_AD_CLIENT_SECRET` | Production only | Production | Azure AD app secret |
| `AZURE_AD_TENANT_ID` | Production only | Production | Azure AD tenant ID |
| `AZURE_AD_REDIRECT_URI` | Production only | Production | OAuth callback URL |
| `AZURE_SQL_SERVER` | Production only | Production | Azure SQL server FQDN |
| `AZURE_SQL_DATABASE` | Production only | Production | Database name |
| `AZURE_SQL_USERNAME` | Production only | Production | SQL admin username |
| `AZURE_SQL_PASSWORD` | Production only | Production | SQL admin password |
| `ENCRYPTION_KEY` | Production only | Production | Database field encryption |

---

## Commands Reference

```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# View logs
docker-compose logs -f web

# Check status
docker-compose ps

# Restart after config changes
docker-compose restart

# Rebuild after code changes
docker-compose build
docker-compose up -d

# Access container shell
docker-compose exec web bash

# Check health endpoint
curl http://localhost:5000/health
```

---

## Support

- **Documentation:** [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)
- **Main README:** [README.md](README.md)
- **Quick Start:** [DOCKER_QUICK_START.md](DOCKER_QUICK_START.md)
