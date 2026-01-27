# Gazelle HL7 v2 Validator Project

## Overview
This application assists developers in validating HL7 v2 Healthlink files before submission to the Healthlink system.
The aim of this project is to determine if an API can be configured so that developers can work from Visual Studio Code to validate HL7 v2 files on Gazelle EVS and get the results back in VS Code.

## Technical Requirements

### Python Environment
- Work with a Python `.venv` virtual environment (with dot prefix)
- Install Python packages using trusted host flags required by company security policy: `--trusted-host pypi.org --trusted-host files.pythonhosted.org`
- Install all required dependencies for working with Healthlink HL7 v2 messages
- Use a `requirements.txt` file to manage dependencies

### Web Framework & Frontend
- Use **Flask** as the web framework
- Use **Bootstrap CDN** for front-end styling
- Use a `styles.css` file for custom styles, located in a `static` directory
- Use a `scripts.js` file for custom JavaScript, located in a `static` directory
- Create HTML templates in a `templates` directory

### Gazelle EVS API Integration

**Base URL:** `https://testing.ehealthireland.ie`

**Key Endpoints:**
- Home: `/evs/home.seam`
- Validator: `/evs/default/validator.seam`
- **REST API Endpoint:** `/evs/rest/validations` (POST)

**API Workflow (from EVS Client documentation):**

1. **Prepare the message:**
   - Encode the HL7 v2 XML message in Base64

2. **Submit validation request:**
   - Send a POST request to `https://testing.ehealthireland.ie/evs/rest/validations`
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
├── app.py
├── requirements.txt
└── vin.xml (sample HL7 v2 file)
```

## Implementation Notes
- The application should provide a web interface for uploading HL7 v2 XML files
- Files should be validated against Gazelle EVS API
- Results should be displayed in a user-friendly format
- Error handling should be robust for API failures and invalid files
