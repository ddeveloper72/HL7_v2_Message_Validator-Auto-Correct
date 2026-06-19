# Docker quick start

This guide starts the HL7 v2 Message Validator in local mode with Docker Compose. See [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md) before enabling production identity and database integrations.

## Prerequisites

- Docker Desktop or Docker Engine with Compose
- A Gazelle EVS API key
- An available local port 5000

## Configure

Create the environment file:

```powershell
Copy-Item .env.docker.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Edit `.env`:

```env
APP_MODE=local
SESSION_SECRET_KEY=replace_with_the_generated_value
GAZELLE_BASE_URL=https://testing.ehealthireland.ie
VERIFY_SSL=true
MAX_AUTO_CORRECT_ITERATIONS=10
```

The web application stores the Gazelle API key in the user session. Enter the key and its validity dates through the profile after startup. `GAZELLE_API_KEY` remains available as an environment fallback for direct validation-script use.

## Build and start

```powershell
docker compose up --build -d
docker compose ps
docker compose logs -f web
```

Open:

- Application: <http://127.0.0.1:5000>
- Health check: <http://127.0.0.1:5000/health>

The health check should return HTTP 200 and a JSON response.

## Common operations

```powershell
# Follow logs
docker compose logs -f web

# Restart the application
docker compose restart web

# Rebuild after dependency or Dockerfile changes
docker compose up --build -d

# Stop the stack
docker compose down
```

The Compose configuration mounts:

| Host path | Container path | Purpose |
| --- | --- | --- |
| `./uploads` | `/app/uploads` | Uploaded source messages |
| `./processed` | `/app/processed` | Corrected output messages |
| `./flask_session` | `/app/flask_session` | Server-side sessions |

These mounts persist across ordinary container recreation. Their retention and backup remain the operator's responsibility.

## Verify the workflow

1. Open the profile and configure the Gazelle API key.
2. Upload one or more approved test messages.
3. Confirm the batch panel reports selected, uploaded, and processed counts.
4. Review the dashboard and individual Gazelle reports.
5. Download and inspect corrected files where applicable.

## Troubleshooting

### Container does not start

```powershell
docker compose ps
docker compose logs web
```

Check that `SESSION_SECRET_KEY` is set, `.env` syntax is valid, and port 5000 is not already in use.

### Health check fails

```powershell
docker compose exec web python -c "import requests; print(requests.get('http://localhost:5000/health', timeout=5).json())"
```

The image health check allows a startup period before marking the service unhealthy. Review the logs for missing packages or configuration errors.

### Files cannot be written

Confirm Docker can write to the mounted host directories. On Linux, also check directory ownership and permissions for the container's non-root user.

### Azure SQL cannot connect

The image uses FreeTDS by default. Confirm Azure SQL firewall rules, credentials, hostname, and `DB_DRIVER=FreeTDS`. See [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md).

### Browser styling is missing

The Content Security Policy permits Tailwind Browser and Lucide from `cdn.jsdelivr.net`. Check browser developer tools for blocked requests and perform a hard refresh.

## Production mode

Do not switch only `APP_MODE`. Production also requires:

- Microsoft Entra ID application settings;
- Azure SQL connection settings;
- a stable session secret;
- a Fernet encryption key;
- an exact production callback URI;
- HTTPS and appropriate network controls.

Follow [DOCKER_CONFIGURATION.md](DOCKER_CONFIGURATION.md) and [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md).

## Related documentation

- [Project README](README.md)
- [Docker configuration](DOCKER_CONFIGURATION.md)
- [Docker deployment](DOCKER_DEPLOYMENT.md)
- [Local development](LOCAL_DEVELOPMENT_GUIDE.md)
- [AI-use disclosure](docs/AI_USE.md)
