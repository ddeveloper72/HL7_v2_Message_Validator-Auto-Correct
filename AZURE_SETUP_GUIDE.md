# Azure AD + SQL Database Setup Guide

## 🎯 Overview
This guide will help you set up Azure AD authentication and SQL database integration for the Gazelle HL7 Validator.

## ✅ What You Already Have
- Azure AD App Registration (Client ID, Secret, Tenant ID configured in .env)
- Azure SQL Database (Server, Database, Username, Password configured)
- Encryption key for API key storage

## 📋 Step-by-Step Setup

### 1. Install Python Dependencies

```bash
cd "c:\Users\Duncan\VS_Code_Projects\HL7_v2_Message_Validator-Auto-Correct"
pip install -r requirements.txt
```

New packages installed:
- `msal` - Azure AD authentication
- `Flask-Session` - Session management
- `pyodbc` - SQL Server database driver
- `cryptography` - Encryption for API keys

### 2. Install ODBC Driver (if not already installed)

Download and install **ODBC Driver 18 for SQL Server**:
- Windows: https://go.microsoft.com/fwlink/?linkid=2249004
- Verify installation: Run `odbcad32.exe` and check "Drivers" tab

### 3. Initialize Database Schema

Connect to your Azure SQL Database and run the schema:

**Option A: Azure Portal Query Editor**
1. Go to https://portal.azure.com
2. Navigate to your database: `<your-database-name>`
3. Click "Query editor"
4. Login with your credentials
5. Copy and paste contents of `database_schema.sql`
6. Click "Run"

**Option B: SQL Server Management Studio (SSMS)**
1. Connect to: `<your-sql-server>.database.windows.net`
2. Open `database_schema.sql`
3. Execute

**Option C: Command Line (sqlcmd)**
```bash
sqlcmd -S <your-sql-server>.database.windows.net -d <your-database-name> -U <your-username> -P <your-password> -i database_schema.sql
```

### 4. Configure Azure AD App Registration

Your app registration needs the correct redirect URI:

1. Go to https://portal.azure.com
2. Navigate to **Azure Active Directory** → **App registrations**
3. Find your app (Client ID: `<your-azure-ad-client-id>`)
4. Go to **Authentication**
5. Add redirect URI: `http://localhost:5000/auth/callback`
6. For production, add: `https://your-app-name.azurewebsites.net/auth/callback`

### 5. Test Database Connection

Run this test script:

```python
python -c "from db_utils import DatabaseManager; db = DatabaseManager(); conn = db.get_connection(); print('✅ Database connected successfully!'); conn.close()"
```

### 6. Start the Application

```bash
python dashboard_app.py
```

Or with Gunicorn:
```bash
gunicorn dashboard_app:app --bind 0.0.0.0:5000 --timeout 120
```

### 7. Test Authentication Flow

1. Open browser: http://localhost:5000
2. Should redirect to login page
3. Click "Sign in with Microsoft"
4. Login with your Azure AD account
5. Should redirect to profile page
6. Add your Gazelle API key
7. Go to Dashboard

## 🔧 Troubleshooting

### Database Connection Errors

**Error: "Login failed for user"**
```bash
# Verify credentials in .env
AZURE_SQL_USERNAME=<your-sql-username>
AZURE_SQL_PASSWORD=<your-sql-password>
```

**Error: "SSL Provider: The certificate chain was issued by an authority that is not trusted"**
```python
# In db_utils.py, the connection already includes:
'Encrypt=yes;'
'TrustServerCertificate=no;'  # Change to 'yes' only for testing
```

**Error: "Cannot open database"**
- Check firewall rules in Azure Portal
- Add your IP address to allowed IPs

### Azure AD Authentication Errors

**Error: "redirect_uri mismatch"**
- Verify redirect URI in Azure AD matches .env
- Must be exact match (including http/https)

**Error: "Invalid client secret"**
- Client secrets expire - check expiration in Azure Portal
- Generate new secret if needed

### Encryption Key Issues

**Error: "Invalid token"**
- Don't change `ENCRYPTION_KEY` after storing API keys
- If you must change it, all users must re-enter API keys

## 📊 Database Tables Created

1. **Users** - User profiles with Azure AD integration
2. **ValidationHistory** - Validation metadata (filename, status, Gazelle URL)
3. **APIKeyAuditLog** - Track when API keys are updated
4. **UserValidationSummary** (View) - User statistics

## 🔒 Security Notes

- API keys are encrypted with Fernet (symmetric encryption)
- Never commit `.env` file to git
- Use Azure Key Vault for production secrets
- Enable Azure AD MFA for users
- Regularly rotate client secrets

## 🚀 Deployment to Azure

### Update Environment Variables

For Azure App Service or Container:

```bash
# Set all .env variables as App Settings
AZURE_AD_CLIENT_ID=...
AZURE_AD_CLIENT_SECRET=...
AZURE_AD_TENANT_ID=...
AZURE_AD_REDIRECT_URI=https://your-app.azurewebsites.net/auth/callback
AZURE_SQL_SERVER=...
AZURE_SQL_DATABASE=...
AZURE_SQL_USERNAME=...
AZURE_SQL_PASSWORD=...
ENCRYPTION_KEY=...
GAZELLE_API_KEY=... (optional default)
```

### Update Redirect URI

Add production redirect URI to Azure AD app registration:
- `https://your-app.azurewebsites.net/auth/callback`

## ✅ Success Checklist

- [ ] Python dependencies installed
- [ ] ODBC Driver installed
- [ ] Database schema created
- [ ] Azure AD redirect URI configured
- [ ] Database connection test passed
- [ ] Application starts without errors
- [ ] Can login with Azure AD
- [ ] Can save API key in profile
- [ ] Can validate messages
- [ ] Validation history shows in database

## 📧 Support

If you encounter issues:
1. Check application logs
2. Verify all .env variables are set
3. Test database connection separately
4. Test Azure AD login separately
5. Check Azure Portal for service health

---

**Ready to go!** 🎉

Your Gazelle HL7 Validator now has:
- ✅ Azure AD single sign-on
- ✅ Encrypted API key storage
- ✅ Validation history tracking
- ✅ User statistics
- ✅ Multi-user support
