# Local development guide

This guide covers the primary Flask dashboard in `dashboard_app.py` on Windows. For a shorter introduction, start with the [project README](README.md).

## Prerequisites

- Python 3.12
- Git
- A Gazelle EVS API key
- Optional: Microsoft ODBC Driver 18 for SQL Server when testing Azure SQL locally

The application calls Gazelle EVS during validation, so an internet connection and access to the configured service are required.

## Create the environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.docker.example .env
```

Generate a session secret:

```powershell
python -c "import secrets; print(secrets.token_hex(32))"
```

Set the minimum local configuration in `.env`:

```env
APP_MODE=local
SESSION_SECRET_KEY=replace_with_the_generated_value
GAZELLE_BASE_URL=https://testing.ehealthireland.ie
VERIFY_SSL=true
MAX_AUTO_CORRECT_ITERATIONS=10
```

Do not commit `.env`.

## Start the application

```powershell
.\.venv\Scripts\Activate.ps1
python dashboard_app.py
```

Open <http://127.0.0.1:5000>. Local mode creates a `Local Developer` session automatically. Configure the Gazelle API key and validity dates on the profile page before validating a message.

The development server reloads when application files change. If configuration, limiter state, or imported module state appears stale, stop and restart the process.

## Local storage behavior

Azure SQL is optional in local mode:

- If the configured database is reachable, the application can use it.
- If SQL is unavailable, the application falls back to temporary processing metadata and filesystem sessions.
- Uploaded and corrected files are written under `uploads/` and `processed/`.
- Temporary result metadata uses the operating system's temporary directory.

Fallback storage is suitable for development, not durable production history.

## Useful checks

Compile the main Python modules:

```powershell
.\.venv\Scripts\python.exe -m compileall dashboard_app.py validate_with_verification.py hl7_corrector.py
```

Check the health endpoint:

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:5000/health
```

Check rendered static assets in the browser developer tools:

- Tailwind Browser and Lucide should load from `cdn.jsdelivr.net`.
- `/static/styles.css` may return `304 Not Modified`; this means the browser cache is current.
- The console should not contain Content Security Policy errors.

Use a hard refresh with `Ctrl+F5` after frontend asset changes.

## Representative manual workflow

1. Open the upload page.
2. Select synthetic or approved Healthlink test messages.
3. Enable auto-correction if required.
4. Confirm selected, uploaded, and processed counts reach the expected totals.
5. Review each validation status and Gazelle report.
6. Download and inspect any corrected message.
7. Confirm the dashboard does not repeatedly poll or return HTTP 429.

Do not use real patient data unless the environment and external service workflow have been formally approved for it.

## Production-mode testing

Production mode requires Microsoft Entra ID, Azure SQL, a stable session secret, and a Fernet encryption key.

```env
APP_MODE=production
AZURE_AD_CLIENT_ID=replace_me
AZURE_AD_CLIENT_SECRET=replace_me
AZURE_AD_TENANT_ID=replace_me
AZURE_AD_REDIRECT_URI=http://localhost:5000/auth/callback
AZURE_SQL_SERVER=replace_me.database.windows.net
AZURE_SQL_DATABASE=replace_me
AZURE_SQL_USERNAME=replace_me
AZURE_SQL_PASSWORD=replace_me
DB_DRIVER=ODBC Driver 18 for SQL Server
ENCRYPTION_KEY=replace_with_a_fernet_key
SESSION_SECRET_KEY=replace_with_a_stable_secret
```

The redirect URI must exactly match the URI registered in Microsoft Entra ID.

## Troubleshooting

### PowerShell blocks virtual-environment activation

Use the interpreter directly:

```powershell
.\.venv\Scripts\python.exe dashboard_app.py
```

### ReportLab is unavailable

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip show reportlab
```

### Azure SQL cannot connect

- Confirm the ODBC driver is installed.
- Confirm the server, database, username, and password.
- Check Azure SQL firewall rules.
- Use local fallback storage when database behavior is not under test.

### Validation fails before reaching Gazelle

- Confirm the API key is configured in the current user session.
- Confirm the key has not expired.
- Check `GAZELLE_BASE_URL` and `VERIFY_SSL`.
- Review Flask CLI output for the validation subprocess result.

## Related documentation

- [Project README](README.md)
- [Docker quick start](DOCKER_QUICK_START.md)
- [Production configuration](DOCKER_CONFIGURATION.md)
- [AI-use disclosure](docs/AI_USE.md)
