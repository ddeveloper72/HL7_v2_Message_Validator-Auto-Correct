# Heroku Deployment Checklist

## Pre-Deployment Checks

### 1. Code Quality & Testing
- [x] All unit tests passing (`test_database_and_autocorrect.py`)
- [x] Integration tests passing (`test_integration_autocorrect.py`)
- [ ] Manual testing complete with local Flask server
- [ ] No syntax errors or warnings
- [x] Security measures verified
- [x] Database connection tested

### 2. Environment Variables Check
Ensure all required variables are set in Heroku:

```bash
heroku config:set AZURE_SQL_SERVER="your-server.database.windows.net"
heroku config:set AZURE_SQL_DATABASE="your-database"
heroku config:set AZURE_SQL_USERNAME="your-username"
heroku config:set AZURE_SQL_PASSWORD="your-password"
heroku config:set ENCRYPTION_KEY="your-encryption-key"
heroku config:set SESSION_SECRET_KEY="your-session-secret"
heroku config:set AZURE_AD_CLIENT_ID="your-client-id"
heroku config:set AZURE_AD_CLIENT_SECRET="your-client-secret"
heroku config:set AZURE_AD_TENANT_ID="your-tenant-id"
heroku config:set AZURE_AD_REDIRECT_URI="https://your-app.herokuapp.com/auth/callback"
heroku config:set GAZELLE_BASE_URL="https://testing.ehealthireland.ie/evs"
heroku config:set VERIFY_SSL="True"
heroku config:set MAX_AUTO_CORRECT_ITERATIONS="10"
```

### 3. Verify Current Heroku Config
```bash
heroku config
```

Check output for:
- [x] All required variables present
- [x] No placeholder values
- [x] Correct database connection string
- [x] Correct Azure AD redirect URI

### 4. Database Verification
- [x] Azure SQL Database accessible
- [x] FreeTDS driver configured (via Aptfile)
- [x] Connection string tested locally
- [x] All database tables exist
- [x] Encryption key works with existing data

### 5. Git Repository
```bash
git status
git add .
git commit -m "Fix: Auto-correct now works with database reports

- Handle db_ prefix in /auto-correct route
- Retrieve files from database for persistent reports
- Fix file read mode (wb -> rb)
- Always save corrected files to database
- Add comprehensive tests
- Maintain security measures"
```

## Deployment Steps

### Step 1: Check Heroku Remote
```bash
git remote -v
```
Should show heroku remote pointing to your app.

If not set:
```bash
heroku git:remote -a your-app-name
```

### Step 2: Deploy
```bash
git push heroku main
```

Or if on a different branch:
```bash
git push heroku your-branch:main
```

### Step 3: Monitor Deployment
Watch the build process for:
- [x] Python buildpack installing
- [x] Aptfile processed (FreeTDS)
- [x] Requirements.txt installing
- [x] No build errors

### Step 4: Check Application Logs
```bash
heroku logs --tail
```

Look for:
- [x] Application starting
- [x] No database connection errors
- [x] No import errors
- [x] Gunicorn workers starting

### Step 5: Restart Dynos (if needed)
```bash
heroku ps:restart
```

## Post-Deployment Verification

### Test 1: Application Accessible
- [ ] Visit https://your-app.herokuapp.com
- [ ] Homepage loads without errors
- [ ] No 500 errors in logs

### Test 2: Azure AD Authentication
- [ ] Click "Login with Azure AD"
- [ ] Authentication flow completes
- [ ] Redirected to dashboard
- [ ] User session created

### Test 3: API Key Functionality
- [ ] Go to Profile
- [ ] Set API key
- [ ] Verify saved successfully
- [ ] Refresh page - key still there (encrypted in DB)

### Test 4: File Upload & Validation
- [ ] Upload HL7 file
- [ ] Validation completes
- [ ] Report appears in dashboard
- [ ] Report saved to database

### Test 5: Auto-Correct (NEW UPLOAD)
- [ ] Find failed validation
- [ ] Click "Try Auto-Correct"
- [ ] Corrections applied
- [ ] New report created
- [ ] File saved to database

### Test 6: Auto-Correct (DATABASE REPORT) 🎯
**THIS IS THE KEY TEST - THE BUG FIX**
- [ ] Close browser / wait for dyno to restart
- [ ] Login again
- [ ] Go to dashboard
- [ ] Reports load from database (db_XXX)
- [ ] Click "Try Auto-Correct" on db_ report
- [ ] **SHOULD WORK NOW** (previously 404 error)
- [ ] Corrections applied successfully
- [ ] New corrected version saved
- [ ] Download works

### Test 7: Database Persistence
- [ ] Logout
- [ ] Login again
- [ ] All reports still visible
- [ ] API key still saved
- [ ] Statistics correct

### Test 8: Download Corrected Files
- [ ] Click download on corrected file
- [ ] File downloads successfully
- [ ] Content correct

## Rollback Plan

If deployment fails:

### Immediate Rollback
```bash
heroku rollback
```

### Check Previous Releases
```bash
heroku releases
```

### Rollback to Specific Version
```bash
heroku rollback v123
```

## Monitoring

### Check Application Health
```bash
heroku ps
```

### View Logs
```bash
heroku logs --tail --source app
```

### View Database Connections
```bash
# Check if app can connect to Azure SQL
heroku run python -c "from db_utils import DatabaseManager; db = DatabaseManager(); conn = db.get_connection(); print('Connected!'); conn.close()"
```

## Common Issues & Solutions

### Issue 1: Database Connection Timeout
**Symptom**: 500 errors, database connection timeouts
**Solution**: 
```bash
# Verify connection string
heroku config:get AZURE_SQL_SERVER
heroku config:get AZURE_SQL_DATABASE

# Check Azure SQL firewall allows Heroku IPs
# Add 0.0.0.0 - 255.255.255.255 or specific Heroku IP ranges
```

### Issue 2: Session Secret Not Set
**Symptom**: Sessions don't persist, users logged out randomly
**Solution**:
```bash
# Generate and set session secret
heroku config:set SESSION_SECRET_KEY="$(openssl rand -hex 32)"
```

### Issue 3: Encryption Key Mismatch
**Symptom**: Cannot decrypt API keys
**Solution**:
- DO NOT change ENCRYPTION_KEY if it's already set
- Changing it will invalidate all stored API keys
- Users must re-enter their API keys

### Issue 4: FreeTDS Driver Not Found
**Symptom**: pyodbc.Error: Driver not found
**Solution**:
- Verify Aptfile exists with FreeTDS
- Check buildpack order (apt buildpack before Python)
- Rebuild:
  ```bash
  heroku buildpacks
  heroku repo:purge_cache
  git commit --allow-empty -m "Rebuild"
  git push heroku main
  ```

## Success Criteria

Deployment is successful when:
- ✅ Application starts without errors
- ✅ Users can login via Azure AD
- ✅ API keys can be saved and retrieved
- ✅ Files can be uploaded and validated
- ✅ Auto-correct works for new uploads
- ✅ **Auto-correct works for database reports (db_XXX)** ← KEY FIX
- ✅ Corrected files can be downloaded
- ✅ Reports persist across sessions
- ✅ No 500 errors in logs
- ✅ Security headers present
- ✅ Rate limiting active

## Performance Monitoring

After deployment, monitor:
- Response times (< 2 seconds for validation)
- Database query times
- Error rates (should be < 1%)
- Memory usage (within dyno limits)
- Auto-correct success rate

## Contact Support

If issues persist:
1. Check Heroku status: https://status.heroku.com
2. Review application logs
3. Test database connectivity
4. Verify environment variables
5. Check Azure AD configuration

## Notes

- Database reports (db_XXX) now fully supported for auto-correct ✅
- File content retrieved from database when temp files unavailable ✅
- Security measures maintained through deployment ✅
- All tests passing locally ✅
