# ⚠️ IMPORTANT: Azure Configuration Required for Production Mode

## Understanding the Two Modes

Your Docker deployment now supports **two distinct modes**:

### 🟢 LOCAL MODE (Default - No Azure Required)
**Status:** ✅ **WORKS OUT OF THE BOX**

**What you get:**
- Full HL7 validation with Gazelle EVS API
- Auto-correction features
- PDF report generation
- Batch file processing
- **No login required** - direct access to dashboard
- **No database** - validation history lost on restart

**What you need:**
- Only a Gazelle API key (already in your .env)

**When to use:**
- Quick testing and development
- Single-user validation
- No need for user authentication
- No need for historical data

**How to use:**
```bash
# Already configured in your .env:
APP_MODE=local

# Just run:
docker-compose up -d

# Access:
http://localhost:5000
```

---

### 🔵 PRODUCTION MODE (Azure Integration Required)
**Status:** ⚠️ **REQUIRES USER'S OWN AZURE SETUP**

**Additional features:**
- **Azure AD authentication** - "Sign in with Microsoft"
- **Multi-user support** - Each user has their own space
- **Validation history** - Stored in Azure SQL Database
- **Encrypted API keys** - Per-user API key storage
- **Audit trails** - Track who validated what and when
- **Session persistence** - Survives container restarts

**What you need:**
1. **Azure Subscription** (free tier works)
2. **Azure AD App Registration** (user must create)
3. **Azure SQL Database** (user must create)
4. **Your organization's email domain** in Azure AD

**When to use:**
- Enterprise deployment
- Multiple team members need access
- Need to track validation history
- Require user authentication
- Need audit compliance

**How to enable:**
```bash
# 1. User must complete Azure setup first (see DOCKER_CONFIGURATION.md)
# 2. Update .env:
APP_MODE=production
AZURE_AD_CLIENT_ID=<from user's Azure AD app>
AZURE_AD_CLIENT_SECRET=<from user's Azure AD app>
AZURE_AD_TENANT_ID=<from user's Azure directory>
AZURE_SQL_SERVER=<from user's Azure SQL>
AZURE_SQL_DATABASE=<from user's Azure SQL>
AZURE_SQL_USERNAME=<from user's Azure SQL>
AZURE_SQL_PASSWORD=<from user's Azure SQL>

# 3. Run:
docker-compose restart
```

---

## Why Can't You Provide Azure Credentials?

### Security & Compliance
1. **Each organization needs their own Azure AD tenant**
   - You can't share Azure AD across organizations
   - Users can only authenticate with their organization's email domain
   - Example: Only @yourcompany.com users can sign into your tenant

2. **Database isolation**
   - Each organization's validation data must be separate
   - Compliance requirements (HIPAA, GDPR) require data isolation
   - You can't share a database between different healthcare organizations

3. **Cost & Billing**
   - Azure resources must be billed to the end user's subscription
   - You can't provide free Azure services (would be your cost)

### What Users Get From Azure Setup

#### Azure AD Benefits
- Single Sign-On (SSO) with their Microsoft 365 accounts
- Centralized user management
- Multi-factor authentication (MFA)
- Conditional access policies
- Integration with their IT security

#### Azure SQL Benefits
- HIPAA/GDPR compliant data storage
- Automatic backups (point-in-time restore)
- High availability (99.99% SLA)
- Encryption at rest and in transit
- Scalable (start small, grow as needed)

---

## Cost Breakdown for Production Mode

### Azure AD App Registration
**Cost:** ✅ **FREE**
- No charge for registering an app
- Works with Azure AD Free tier
- Takes 5 minutes to set up

### Azure SQL Database
**Minimum Cost:** ~$5/month (Basic tier)
- 2GB storage
- Sufficient for thousands of validation records
- Can scale up if needed

**Free Alternative:** Azure SQL Database Free Offer
- 32GB storage for 12 months
- Good for testing and small teams
- Requires Azure free account

### Total Monthly Cost
- **Development/Testing:** $0 (use local mode)
- **Small team (1-10 users):** $5/month (Basic SQL)
- **Larger deployment:** $10-50/month (Standard SQL tier)

---

## Deployment Decision Matrix

| Feature | Local Mode | Production Mode |
|---------|------------|-----------------|
| **Setup Time** | 5 minutes | 30 minutes |
| **Azure Required** | ❌ No | ✅ Yes |
| **Monthly Cost** | $0 | ~$5+ |
| **User Authentication** | ❌ None | ✅ Azure AD SSO |
| **Multiple Users** | ⚠️ Shared session | ✅ Isolated per user |
| **Validation History** | ⚠️ Lost on restart | ✅ Persistent |
| **API Key Storage** | ⚠️ Session only | ✅ Encrypted in DB |
| **Audit Trail** | ❌ None | ✅ Full tracking |
| **Best For** | Testing, dev, single user | Teams, enterprise, compliance |

---

## Recommended Approach

### 1. Start with Local Mode (Everyone)
```bash
# Use your current .env with APP_MODE=local
docker-compose up -d
```
✅ Test all features  
✅ Validate files  
✅ Generate reports  
✅ Evaluate the application  

### 2. Upgrade to Production (When Needed)

**Triggers to upgrade:**
- More than one person needs access
- Need to track validation history
- Require user authentication
- Compliance/audit requirements
- Want integration with Microsoft 365

**Time Investment:** ~30 minutes one-time setup

**Follow:** [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md) - Production Mode section

---

## Your Current Configuration

```bash
# In your .env:
APP_MODE=local          # ✅ Set to local mode
GAZELLE_API_KEY=<set>   # ✅ Configured

# Container status:
Status: Up and healthy
Mode: LOCAL
Azure AD: DISABLED
Database: In-memory only

# Access:
http://localhost:5000   # ✅ Working
```

**Everything is working correctly!** 🎉

---

## Sharing with Other Users

### If you distribute this Docker image to other users:

1. **For local mode (simple):**
   - Give them `.env.docker.example`
   - They add their own `GAZELLE_API_KEY`
   - Works immediately, no Azure needed

2. **For production mode (enterprise):**
   - Give them `.env.docker.example`
   - Give them `DOCKER_CONFIGURATION.md`
   - They complete their own Azure setup
   - Takes ~30 minutes per organization

### What users must provide themselves:
- ✅ Their own Gazelle API key (always)
- ✅ Their own Azure AD tenant (production only)
- ✅ Their own Azure SQL Database (production only)

### What you can provide:
- ✅ Docker image
- ✅ Configuration templates
- ✅ Documentation
- ✅ Setup guides
- ❌ Cannot provide Azure credentials (security/compliance)

---

## Questions?

### "Can I use your Azure AD?"
❌ **No** - Each organization needs their own Azure AD tenant. Users can only authenticate with their organization's email domain.

### "Can I use your Azure SQL Database?"
❌ **No** - Healthcare data must be isolated per organization for compliance (HIPAA/GDPR).

### "Do I have to use production mode?"
❌ **No** - Local mode is fully functional for single-user validation. Only upgrade if you need authentication and multi-user features.

### "Can I test production mode without Azure?"
❌ **No** - But local mode has all the validation features. Production mode only adds authentication and history tracking.

### "Is Azure required for the app to work?"
❌ **No** - The app works perfectly in local mode with just a Gazelle API key. Azure is only needed for enterprise features (auth, multi-user, history).

---

## Summary

✅ **Local mode:** Works out of the box, no Azure required  
⚠️ **Production mode:** User must provide their own Azure credentials  
📚 **Full setup guide:** [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md)  
🎯 **Recommendation:** Start with local mode, upgrade if needed  

---

**Last Updated:** May 20, 2026  
**Current Status:** Docker fully operational in both modes ✅
