# Heroku Deployment Guide

## 📦 What's Included in Deployment

### Production Files (Deployed to Heroku):
- `dashboard_app.py` - Main Flask application
- `hl7_corrector.py` - Auto-correction module (5 correction methods)
- `validate_with_verification.py` - Gazelle EVS validation script
- `templates/` - All HTML templates
- `static/` - CSS, JavaScript, and favicon
- `requirements.txt` - Python dependencies
- `Procfile` - Heroku process configuration
- `runtime.txt` - Python version specification (3.12.4)
- `.slugignore` - Files to exclude from deployment slug

### Excluded from Deployment:
- All test files (`test_*.py`, `verify_*.py`, etc.)
- Development tools (`diagnose_*.py`, `debug_*.py`, `fix_*.py`)
- Test data folders (`Healthlink Tests/`, `HL7_v2_Schemas/`)
- Documentation files (*.md except README.md)
- Old simple app (`app.py`)
- Runtime folders (`uploads/`, `processed/`, `batch_results/`)
- Virtual environment (`.venv/`)
- Environment variables file (`.env`)

## 🚀 Deployment Steps

### 1. Prerequisites
- Heroku account created
- Heroku CLI installed: https://devcenter.heroku.com/articles/heroku-cli
- Git repository initialized (✅ Done)

### 2. Login to Heroku
```bash
heroku login
```

### 3. Create Heroku App
```bash
heroku create your-app-name
# Example: heroku create hl7-gazelle-validator
```

### 4. Set Environment Variables
```bash
heroku config:set GAZELLE_API_KEY=your_api_key_here
heroku config:set VERIFY_SSL=True
```

### 5. Install Playwright Browser (Post-deployment)
Playwright needs to download Chromium browser after deployment. Add this to your deployment:

```bash
# This will be handled by Heroku buildpack
heroku buildpacks:add --index 1 https://github.com/mxschmitt/heroku-playwright-buildpack.git
heroku buildpacks:add --index 2 heroku/python
```

### 6. Deploy to Heroku
```bash
git push heroku main
```

### 7. Scale the Web Dyno
```bash
heroku ps:scale web=1
```

### 8. Open Your App
```bash
heroku open
```

## 🔧 Configuration Details

### Procfile
```
web: gunicorn dashboard_app:app --timeout 120
```
- Uses `gunicorn` as production WSGI server
- 120-second timeout for long-running validation requests

### Runtime
```
python-3.12.4
```
- Matches your local development environment

### Environment Variables Required
- `GAZELLE_API_KEY` - Your Gazelle EVS API key
- `VERIFY_SSL` - SSL verification (default: True)

## 📊 Expected Deployment Size
- **With .slugignore**: ~50-100 MB (lean deployment)
- **Without .slugignore**: ~500+ MB (includes test data and schemas)

The `.slugignore` file reduces deployment size by ~80%!

## 🔍 Monitoring & Logs

### View Logs
```bash
heroku logs --tail
```

### Check App Status
```bash
heroku ps
```

### Restart App
```bash
heroku restart
```

## ⚙️ Post-Deployment Setup

### Initialize Playwright Browsers
After first deployment, you may need to manually install Playwright browsers:

```bash
heroku run playwright install chromium
```

Or add a `heroku-release.sh` script:
```bash
#!/bin/bash
playwright install chromium
```

And update Procfile:
```
release: bash heroku-release.sh
web: gunicorn dashboard_app:app --timeout 120
```

## 🐛 Troubleshooting

### Issue: Playwright browser not found
**Solution**: Add Playwright buildpack (see step 5 above)

### Issue: Timeout during validation
**Solution**: Increase timeout in Procfile:
```
web: gunicorn dashboard_app:app --timeout 180
```

### Issue: Application error
**Solution**: Check logs:
```bash
heroku logs --tail
```

### Issue: Environment variables not set
**Solution**: Verify config:
```bash
heroku config
```

## 📝 Local Testing Before Deployment

Test production configuration locally:

```bash
# Install gunicorn
pip install gunicorn

# Run with gunicorn (production mode)
gunicorn dashboard_app:app --timeout 120

# Test at http://localhost:8000
```

## 🔄 Updating the Deployment

After making changes:

```bash
git add .
git commit -m "Description of changes"
git push heroku main
```

Heroku will automatically:
1. Detect changes
2. Install dependencies from requirements.txt
3. Restart the application
4. Use the updated code

## 📚 Additional Resources

- [Heroku Python Guide](https://devcenter.heroku.com/articles/getting-started-with-python)
- [Heroku Config Vars](https://devcenter.heroku.com/articles/config-vars)
- [Playwright on Heroku](https://github.com/microsoft/playwright/issues/10750)

## ✅ Deployment Checklist

- [x] All production files committed to git
- [x] `.slugignore` created to reduce deployment size
- [x] `Procfile` configured with gunicorn
- [x] `runtime.txt` specifies Python 3.12.4
- [x] `requirements.txt` includes all dependencies + gunicorn
- [x] `.gitignore` excludes sensitive files (.env)
- [x] Environment variables documented
- [ ] Heroku app created
- [ ] Playwright buildpack added
- [ ] Environment variables set on Heroku
- [ ] App deployed and tested
- [ ] PDF export with emojis tested in production

---

**Ready to deploy!** 🚀
