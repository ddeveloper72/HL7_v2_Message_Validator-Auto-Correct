# Gazelle HL7 v2 Validator Project

## Overview
This application assists developers in validating HL7 v2 Healthlink files before submission.
The application provides a web interface for validating HL7 v2 files using Gazelle EVS API.

## Technical Requirements

### Python Environment
- Work with a Python `.venv` virtual environment (with dot prefix)
- Install Python packages using pip from requirements.txt
- Use environment variables for configuration (stored in .env file)

### Web Framework & Frontend
- Use **Flask** as the web framework
- Use **Bootstrap CDN** for front-end styling
- Use a `styles.css` file for custom styles, located in a `static` directory
- Use a `scripts.js` file for custom JavaScript, located in a `static` directory
- Create HTML templates in a `templates` directory

### Gazelle EVS API Integration

**Configuration via Environment Variables:**
- `GAZELLE_BASE_URL` - Base URL for Gazelle EVS instance
- `GAZELLE_API_KEY` - (Optional) API key for local development
- `VERIFY_SSL` - SSL verification setting

**API Workflow (from EVS Client documentation):**

1. **Prepare the message:**
   - Encode the HL7 v2 XML message in Base64

2. **Submit validation request:**
   - Send a POST request to the REST API validation endpoint
   - Include the Base64-encoded message in the request body
   - The response will include:
     - Global validation status
     - URL of the validation report

3. **Retrieve validation report:**
   - Use a GET request to fetch the full validation report from the URL provided in step 2

## Project Structure
```
Gazelle/
├── .github/
│   └── copilot-instructions.md
├── .venv/
├── static/
│   ├── styles.css
│   └── scripts.js
├── templates/
│   └── index.html
├── dashboard_app.py
├── hl7_corrector.py
├── validate_with_verification.py
├── requirements.txt
└── .env (local only - not committed)
```

## Implementation Notes
- The application should provide a web interface for uploading HL7 v2 XML files
- Files should be validated against Gazelle EVS API
- Results should be displayed in a user-friendly format
- Error handling should be robust for API failures and invalid files
- Each user provides their own API key (stored in session)