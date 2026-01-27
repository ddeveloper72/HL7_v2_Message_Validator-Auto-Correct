from flask import Flask, render_template, request, jsonify
import requests
import base64
import os
import traceback
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = 'uploads'

# Gazelle EVS API configuration
EVS_BASE_URL = 'https://testing.ehealthireland.ie'
EVS_VALIDATION_ENDPOINT = f'{EVS_BASE_URL}/evs/rest/validations'

# API Key from environment variable
GAZELLE_API_KEY = os.getenv('GAZELLE_API_KEY', '')

# Default validator for HL7 v2.4 messages (can be changed)
# Format: MessageType^TriggerEvent^MessageStructure / Version / System / Profile / Domain
DEFAULT_VALIDATOR = 'ORU^R01^ORU_R01'  # For ORU messages
# Other options: REF^I12^REF_I12, ADT^A01^ADT_A01, etc.

# SSL verification (from environment or default to True)
VERIFY_SSL = os.getenv('VERIFY_SSL', 'True').lower() in ('true', '1', 'yes')

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/')
def index():
    """Render the main page."""
    return render_template('index.html')


@app.route('/test', methods=['GET'])
def test():
    """Test endpoint to verify Flask is working."""
    return jsonify({
        'status': 'ok',
        'message': 'Flask is working correctly!',
        'config': {
            'EVS_BASE_URL': EVS_BASE_URL,
            'EVS_VALIDATION_ENDPOINT': EVS_VALIDATION_ENDPOINT,
            'VERIFY_SSL': VERIFY_SSL
        }
    })


@app.route('/test-api', methods=['POST'])
def test_api_formats():
    """Test different API request formats."""
    try:
        sample_file_path = os.path.join(os.path.dirname(__file__), 'vin.xml')
        with open(sample_file_path, 'rb') as f:
            xml_content = f.read()
        
        base64_encoded = base64.b64encode(xml_content).decode('utf-8')
        results = []
        
        # Test 1: application/base64
        try:
            r = requests.post(EVS_VALIDATION_ENDPOINT, data=base64_encoded, 
                            headers={'Content-Type': 'application/base64'}, timeout=10, verify=VERIFY_SSL)
            results.append({'format': 'application/base64', 'status': r.status_code, 'response': r.text[:200]})
        except Exception as e:
            results.append({'format': 'application/base64', 'error': str(e)})
        
        # Test 2: text/plain with base64
        try:
            r = requests.post(EVS_VALIDATION_ENDPOINT, data=base64_encoded,
                            headers={'Content-Type': 'text/plain'}, timeout=10, verify=VERIFY_SSL)
            results.append({'format': 'text/plain (base64)', 'status': r.status_code, 'response': r.text[:200]})
        except Exception as e:
            results.append({'format': 'text/plain (base64)', 'error': str(e)})
        
        # Test 3: application/xml with raw XML
        try:
            r = requests.post(EVS_VALIDATION_ENDPOINT, data=xml_content,
                            headers={'Content-Type': 'application/xml'}, timeout=10, verify=VERIFY_SSL)
            results.append({'format': 'application/xml (raw)', 'status': r.status_code, 'response': r.text[:200]})
        except Exception as e:
            results.append({'format': 'application/xml (raw)', 'error': str(e)})
        
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/validate', methods=['POST'])
def validate_hl7():
    """
    Validate HL7 v2 XML file using Gazelle EVS API.
    
    Based on Swagger API specification v3.0:
    - POST to /evs/rest/validations with JSON payload
    - Content must be base64-encoded (EVS-45)
    - Must provide either (validationService + validator) OR objectType (EVS-46)
    - Returns 201 Created with Location header containing OID
    - Get full report from {location}/report
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read and validate file is XML
        if not file.filename.lower().endswith('.xml'):
            return jsonify({'error': 'File must be an XML file'}), 400
        
        # Read file content
        xml_content = file.read()
        
        # Encode in base64 as required by EVS-45
        base64_content = base64.b64encode(xml_content).decode('utf-8')
        
        # Prepare validation request according to Swagger spec
        # EVS-46: Must provide either (validationService + validator) OR objectType
        # WORKING CONFIGURATION: Use validationService with OID from validator dropdown
        payload = {
            "objects": [
                {
                    "originalFileName": file.filename,
                    "content": base64_content
                }
            ],
            "validationService": {
                "name": "Gazelle HL7v2.x validator",
                "validator": "1.3.6.1.4.1.12559.11.35.10.1.20"  # REF^I12^REF_I12 OID
            }
        }
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Add API key if configured (EVS-51)
        if GAZELLE_API_KEY:
            headers['Authorization'] = f'GazelleAPIKey {GAZELLE_API_KEY}'
        
        # Make API request
        response = requests.post(
            EVS_VALIDATION_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=30,
            verify=VERIFY_SSL
        )
        
        # Handle different response codes
        if response.status_code == 201:
            # Successful validation (EVS-17)
            location = response.headers.get('Location')
            redirect_url = response.headers.get('X-Validation-Report-Redirect')
            
            # Extract the validation OID from Location header
            oid = location.split('/')[-1] if location else None
            
            result = {
                'success': True,
                'status': 'completed',
                'filename': file.filename,
                'oid': oid,
                'location': location,
                'redirect_url': redirect_url
            }
            
            # Fetch the full validation report
            if location:
                try:
                    report_response = requests.get(
                        location,
                        headers={'Accept': 'application/json'},
                        timeout=30,
                        verify=VERIFY_SSL
                    )
                    if report_response.status_code == 200:
                        validation_data = report_response.json()
                        result['validation_status'] = validation_data.get('status', 'Unknown')
                        result['report_url'] = validation_data.get('validationReportRef', {}).get('location')
                        
                        # Try to get the detailed report
                        report_url = result.get('report_url')
                        if report_url:
                            detailed_report = requests.get(
                                report_url,
                                headers={'Accept': 'application/json'},
                                timeout=30,
                                verify=VERIFY_SSL
                            )
                            if detailed_report.status_code == 200:
                                result['detailed_report'] = detailed_report.text
                except Exception as e:
                    result['report_error'] = f'Failed to fetch report: {str(e)}'
            
            return jsonify(result)
            
        elif response.status_code == 202:
            # Accepted for async processing (EVS-18)
            location = response.headers.get('Location')
            return jsonify({
                'success': True,
                'status': 'pending',
                'message': 'Validation request accepted, processing asynchronously',
                'location': location,
                'filename': file.filename
            })
            
        elif response.status_code == 400:
            # Bad Request (EVS-47, EVS-48)
            return jsonify({
                'error': 'Bad Request - Invalid validation request',
                'details': response.text,
                'status_code': 400
            }), 400
            
        elif response.status_code == 401:
            # Unauthorized (EVS-49)
            return jsonify({
                'error': 'Unauthorized - Invalid or missing API key',
                'details': response.text,
                'status_code': 401
            }), 401
            
        else:
            # Other errors
            return jsonify({
                'error': f'Validation request failed with status {response.status_code}',
                'details': response.text,
                'status_code': response.status_code
            }), response.status_code
        
    except requests.exceptions.Timeout:
        error_msg = 'Request to Gazelle EVS timed out'
        app.logger.error(error_msg)
        return jsonify({'error': error_msg}), 504
    
    except requests.exceptions.RequestException as e:
        error_msg = f'Network error: {str(e)}'
        error_trace = traceback.format_exc()
        app.logger.error(f'{error_msg}\\n{error_trace}')
        return jsonify({
            'error': error_msg,
            'traceback': error_trace
        }), 500
    
    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        error_trace = traceback.format_exc()
        app.logger.error(f'{error_msg}\\n{error_trace}')
        return jsonify({
            'error': error_msg,
            'traceback': error_trace
        }), 500


@app.route('/validate-sample', methods=['POST'])
def validate_sample():
    """Validate the sample vin.xml file using correct Swagger API format."""
    try:
        sample_file_path = os.path.join(os.path.dirname(__file__), 'vin.xml')
        
        if not os.path.exists(sample_file_path):
            return jsonify({'error': 'Sample file vin.xml not found'}), 404
        
        with open(sample_file_path, 'rb') as f:
            xml_content = f.read()
        
        # Encode in base64 as required by EVS-45
        base64_content = base64.b64encode(xml_content).decode('utf-8')
        
        # Prepare validation request according to Swagger spec
        # WORKING CONFIGURATION: Use validationService with OID from validator dropdown
        payload = {
            "objects": [
                {
                    "originalFileName": "vin.xml",
                    "content": base64_content
                }
            ],
            "validationService": {
                "name": "Gazelle HL7v2.x validator",
                "validator": "1.3.6.1.4.1.12559.11.35.10.1.20"  # REF^I12^REF_I12 OID
            }
        }
        
        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Add API key if configured (EVS-51)
        if GAZELLE_API_KEY:
            headers['Authorization'] = f'GazelleAPIKey {GAZELLE_API_KEY}'
        
        # Make API request
        response = requests.post(
            EVS_VALIDATION_ENDPOINT,
            json=payload,
            headers=headers,
            timeout=30,
            verify=VERIFY_SSL
        )
        
        # Handle response
        if response.status_code == 201:
            location = response.headers.get('Location')
            oid = location.split('/')[-1] if location else None
            
            result = {
                'success': True,
                'status': 'completed',
                'filename': 'vin.xml',
                'oid': oid,
                'location': location
            }
            
            # Fetch validation details
            if location:
                try:
                    report_response = requests.get(
                        location,
                        headers={'Accept': 'application/json'},
                        timeout=30,
                        verify=VERIFY_SSL
                    )
                    if report_response.status_code == 200:
                        validation_data = report_response.json()
                        result['validation_status'] = validation_data.get('status', 'Unknown')
                        result['report_url'] = validation_data.get('validationReportRef', {}).get('location')
                except Exception as e:
                    result['report_error'] = f'Failed to fetch report: {str(e)}'
            
            return jsonify(result)
        elif response.status_code == 202:
            return jsonify({
                'success': True,
                'status': 'pending',
                'filename': 'vin.xml',
                'location': response.headers.get('Location')
            })
        else:
            return jsonify({
                'error': f'Validation failed with status {response.status_code}',
                'details': response.text
            }), response.status_code
        
    except Exception as e:
        error_msg = f'Error validating sample: {str(e)}'
        error_trace = traceback.format_exc()
        app.logger.error(f'{error_msg}\\n{error_trace}')
        return jsonify({
            'error': error_msg,
            'traceback': error_trace
        }), 500


if __name__ == '__main__':
    print("Starting Flask application...")
    print(f"EVS API Endpoint: {EVS_VALIDATION_ENDPOINT}")
    print(f"SSL Verification: {VERIFY_SSL}")
    print(f"API Key Configured: {'Yes' if GAZELLE_API_KEY else 'No'}")
    if not GAZELLE_API_KEY:
        print("\n⚠ WARNING: No API key found in .env file")
        print("  Add GAZELLE_API_KEY=<your-key> to .env file if required\n")
    try:
        app.run(debug=True, host='127.0.0.1', port=5000, use_reloader=False)
    except Exception as e:
        print(f"Error starting Flask: {e}")
        traceback.print_exc()
