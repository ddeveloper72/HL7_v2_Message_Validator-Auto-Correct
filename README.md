# Gazelle HL7 v2 Validator

A web application for validating HL7 v2 Healthlink XML files using the Gazelle EVS API before submission to the Healthlink system.

## Features

- 🔍 **File Upload & Validation**: Upload HL7 v2 XML files for validation
- 📋 **Sample Validation**: Test with the included sample file (vin.xml)
- 📊 **Detailed Reports**: View comprehensive validation reports
- 🎨 **Modern UI**: Clean Bootstrap-based interface
- 🔗 **Direct Links**: Access full validation reports on Gazelle EVS

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
├── vin.xml
└── README.md
```

## Installation

### 1. Create Python Virtual Environment

```bash
python -m venv .venv
```

### 2. Install Dependencies

Install using trusted host flags (required by company security policy):

```bash
.venv\Scripts\pip.exe install --trusted-host pypi.org --trusted-host files.pythonhosted.org Flask Werkzeug requests
```

Or install from requirements.txt:
```bash
.venv\Scripts\pip.exe install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## Usage

### Starting the Application

Run the Flask application:

```bash
.venv\Scripts\python.exe app.py
```

The application will start on `http://127.0.0.1:5000`

### Using the Web Interface

1. Open your web browser and navigate to `http://127.0.0.1:5000`
2. Choose one of two options:
   - **Upload File**: Select an HL7 v2 XML file from your computer
   - **Validate Sample**: Test with the included vin.xml sample file
3. Click the validation button
4. View the results:
   - Validation status (Success/Error/Warning)
   - Full validation report
   - Link to detailed report on Gazelle EVS
   - Raw API response (expandable)

## API Endpoints

### POST /validate
Validates an uploaded HL7 v2 XML file.

**Request:**
- Method: POST
- Content-Type: multipart/form-data
- Body: file (XML file)

**Response:**
```json
{
  "success": true,
  "filename": "example.xml",
  "validation_status": "PASSED",
  "report_url": "https://...",
  "report": "...",
  "initial_response": {...}
}
```

### POST /validate-sample
Validates the sample vin.xml file.

**Request:**
- Method: POST

**Response:** Same as /validate endpoint

## How It Works

The application implements the Gazelle EVS API workflow:

1. **Encode**: The XML file is encoded in Base64
2. **Submit**: POST request to `https://testing.ehealthireland.ie/evs/rest/validations`
3. **Response**: Receives validation status and report URL
4. **Retrieve**: GET request to fetch the full validation report
5. **Display**: Shows results in a user-friendly format

## Configuration

### Gazelle EVS Settings
- **Base URL**: `https://testing.ehealthireland.ie`
- **Validation Endpoint**: `/evs/rest/validations`

### Application Settings
- **Host**: 127.0.0.1
- **Port**: 5000
- **Debug Mode**: Enabled (development)
- **Max File Size**: 16MB

## Development

### Technology Stack
- **Backend**: Flask (Python web framework)
- **Frontend**: Bootstrap 5.3.2
- **Icons**: Bootstrap Icons 1.11.3
- **HTTP Client**: requests library

### File Structure
- `app.py`: Flask application with validation logic
- `templates/index.html`: Main web interface
- `static/styles.css`: Custom styling
- `static/scripts.js`: Client-side JavaScript
- `requirements.txt`: Python dependencies

## Security Notes

As per company policy, when reinstalling packages use trusted host flags:
```bash
.venv\Scripts\pip.exe install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## Troubleshooting

### Common Issues

**Port Already in Use**
```bash
# Change port in app.py:
app.run(debug=True, host='127.0.0.1', port=5001)
```

**Module Not Found**
```bash
# Ensure virtual environment is activated and packages are installed
pip install -r requirements.txt
```

**CORS/Network Errors**
- Verify internet connection
- Check Gazelle EVS endpoint availability
- Confirm firewall settings allow outbound HTTPS

## Sample File

The included `vin.xml` file is a sample HL7 v2 REF_I12 message that can be used for testing the validation workflow.

## License

Internal development tool for Healthlink HL7 v2 validation.

## Support

For issues with:
- **Application**: Check error messages in the browser console and terminal
- **Gazelle EVS API**: Visit https://testing.ehealthireland.ie/evs/home.seam
- **HL7 v2 Standards**: Refer to HL7 v2.4 documentation
