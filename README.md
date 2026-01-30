# Gazelle HL7 v2 Validator

A web application for validating HL7 v2 Healthlink XML files using the Gazelle EVS API.

## Features

- 🔍 **File Upload & Validation**: Upload HL7 v2 XML files for validation
- 🤖 **Auto-Correction**: Automatically fixes common HL7 message errors
- 📊 **Detailed Reports**: View comprehensive validation reports with error analysis
- 📄 **PDF Export**: Export validation reports as PDF with emoji support
- 🔐 **User API Keys**: Each user provides their own Gazelle API key
- 🎨 **Modern UI**: Clean Bootstrap-based dashboard interface

## Quick Start

### 1. Create Python Virtual Environment

```bash
python -m venv .venv
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

Create a `.env` file in the project root:

```env
# Gazelle EVS API Configuration
GAZELLE_API_KEY=your_api_key_here
GAZELLE_BASE_URL=https://your-gazelle-instance
VERIFY_SSL=True
```

### 4. Run the Application

```bash
python dashboard_app.py
```

The application will start on `http://127.0.0.1:5000`

## Usage

### Web Interface

1. Open your browser to `http://127.0.0.1:5000`
2. Enter your Gazelle API key (stored in your session only)
3. Upload HL7 v2 XML files via drag-and-drop or file browser
4. View validation results with detailed error reports
5. Use auto-correction for failed validations
6. Export reports as PDF

### API Key

Each user must provide their own Gazelle API key:
- Keys are stored in encrypted Flask sessions (not persisted)
- API key identifies you to the Gazelle validation service
- Obtain your API key from your Gazelle account profile

## Configuration

All configuration is managed through environment variables in `.env`:

- `GAZELLE_BASE_URL` - Base URL for your Gazelle EVS instance
- `GAZELLE_API_KEY` - (Optional) Your personal API key for local development
- `VERIFY_SSL` - Enable/disable SSL verification (default: True)

**Note**: The `.env` file is excluded from version control for security.

## Development

### Technology Stack
- **Backend**: Flask, Python 3.12
- **Frontend**: Bootstrap 5.3, JavaScript
- **PDF Generation**: Playwright (headless browser)
- **Validation**: Gazelle EVS REST API

### Project Structure
```
Gazelle/
├── dashboard_app.py          # Main application
├── hl7_corrector.py          # Auto-correction module
├── validate_with_verification.py  # Validation script
├── templates/                # HTML templates
├── static/                   # CSS, JS, images
├── requirements.txt          # Python dependencies
├── Procfile                  # Heroku deployment
├── runtime.txt               # Python version
└── .env                      # Environment config (local only)
```

## Deployment

### Heroku

1. Create a new Heroku app
2. Add buildpacks:
   ```bash
   heroku buildpacks:add https://github.com/mxschmitt/heroku-playwright-buildpack.git
   heroku buildpacks:add heroku/python
   ```
3. Set stack to heroku-22:
   ```bash
   heroku stack:set heroku-22
   ```
4. Deploy via GitHub integration or:
   ```bash
   git push heroku main
   ```

**Note**: No `GAZELLE_API_KEY` environment variable needed - users provide their own keys.

## Security

- ✅ User API keys stored in encrypted sessions only
- ✅ No credentials committed to version control
- ✅ SSL verification enabled by default
- ✅ Environment variables for configuration
- ✅ `.gitignore` prevents sensitive file commits

## Auto-Correction Features

The application automatically corrects common HL7 v2 errors:

1. **BOM Removal** - Strips UTF-8 byte order marks
2. **XML Declaration** - Adds proper XML headers
3. **Code Corrections** - Fixes invalid HL7 table codes
4. **Field Insertions** - Fills required empty fields

## License

Internal development tool for HL7 v2 validation.

