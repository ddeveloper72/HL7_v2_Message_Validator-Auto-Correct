"""
Gazelle HL7 v2 Validation Dashboard
Web interface for validating HL7 messages and viewing reports
"""
from flask import Flask, render_template, request, send_file, session, redirect, url_for, jsonify
import os
import markdown
from datetime import datetime
import json
from pathlib import Path
from io import BytesIO
from playwright.sync_api import sync_playwright
import uuid
import shutil
from werkzeug.utils import secure_filename
import subprocess
import threading
import requests
from xml.etree import ElementTree as ET
from auto_correct import auto_correct_and_validate
from hl7_corrector import HL7MessageCorrector
import time
import sys

app = Flask(__name__)

# Session configuration - use environment variable or fallback for development
session_secret = os.environ.get('SESSION_SECRET_KEY')
if not session_secret:
    # For local development only - generate a persistent key
    if os.path.exists('.session_secret'):
        with open('.session_secret', 'r') as f:
            session_secret = f.read().strip()
    else:
        session_secret = os.urandom(24).hex()
        # Don't save for Heroku - it needs to be set as an environment variable
        if not os.environ.get('DYNO'):  # Only save locally (not on Heroku)
            with open('.session_secret', 'w') as f:
                f.write(session_secret)

app.secret_key = session_secret

# Configure session to be more compatible with multiple workers
app.config['SESSION_COOKIE_SECURE'] = True  # Only send over HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days

# Configure folders
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
REPORTS_FOLDER = 'Healthlink Tests'  # Using existing test reports
ALLOWED_EXTENSIONS = {'txt', 'xml'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Store processing results in memory + temp file (Heroku-compatible)
# Results are stored in /tmp so they persist for the dyno lifetime
processing_results = {}
RESULTS_TEMP_FILE = '/tmp/processing_results.json'

def load_processing_results():
    """Load processing results from temp file"""
    global processing_results
    if os.path.exists(RESULTS_TEMP_FILE):
        try:
            with open(RESULTS_TEMP_FILE, 'r') as f:
                processing_results = json.load(f)
                print(f"DEBUG: Loaded {len(processing_results)} results from temp file")
        except Exception as e:
            print(f"DEBUG: Error loading results from temp file: {e}")
            processing_results = {}
    else:
        print("DEBUG: No temp file found, starting with empty results")

def save_processing_results():
    """Save processing results to temp file"""
    try:
        with open(RESULTS_TEMP_FILE, 'w') as f:
            json.dump(processing_results, f)
    except Exception as e:
        print(f"DEBUG: Error saving results to temp file: {e}")

# Load existing results on startup
load_processing_results()

def fetch_and_parse_gazelle_report(oid, api_key):
    """Fetch XML report from Gazelle and parse detailed errors/warnings"""
    try:
        xml_url = f"https://testing.ehealthireland.ie/evs/rest/validations/{oid}/report"
        headers = {
            "Accept": "application/xml",
            "Authorization": f"GazelleAPIKey {api_key}"
        }
        xml_response = requests.get(xml_url, headers=headers, timeout=10)
        
        if xml_response.status_code != 200:
            return None, None, None
        
        xml_report = xml_response.text
        root = ET.fromstring(xml_report)
        ns = {'gvr': 'http://validationreport.gazelle.ihe.net/'}
        
        detailed_errors = []
        detailed_warnings = []
        
        constraints = root.findall('.//gvr:constraint', ns)
        
        for constraint in constraints:
            priority = constraint.get('priority', '')
            severity = constraint.get('severity', '')
            test_result = constraint.get('testResult', '')
            
            if test_result == 'FAILED':
                desc_elem = constraint.find('gvr:constraintDescription', ns)
                loc_elem = constraint.find('gvr:locationInValidatedObject', ns)
                type_elem = constraint.find('gvr:constraintType', ns)
                
                issue = {
                    'description': desc_elem.text if desc_elem is not None else 'Unknown',
                    'location': loc_elem.text if loc_elem is not None else 'Unknown',
                    'type': type_elem.text if type_elem is not None else 'Unknown',
                    'priority': priority,
                    'severity': severity
                }
                
                if priority == 'MANDATORY' and severity == 'ERROR':
                    detailed_errors.append(issue)
                elif priority == 'RECOMMENDED' and severity == 'WARNING':
                    detailed_warnings.append(issue)
        
        return detailed_errors, detailed_warnings, xml_report
    except Exception as e:
        print(f"Error fetching Gazelle report: {e}")
        return None, None, None

def get_sample_reports():
    """Get user's validation reports"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    reports = []
    
    # Only show session-uploaded files (user's own validations)
    if 'session_id' in session:
        print(f"DEBUG: Getting reports for session_id: {session['session_id']}")
        print(f"DEBUG: Total items in processing_results: {len(processing_results)}")
        for file_id, info in processing_results.items():
            print(f"DEBUG: Checking file_id={file_id}, session_id={info.get('session_id')}, status={info.get('status')}")
            if info.get('session_id') == session['session_id'] and info.get('status') == 'completed':
                validated_at = info.get('validated_at', datetime.now().isoformat())
                if isinstance(validated_at, str):
                    validated_at = datetime.fromisoformat(validated_at)
                else:
                    validated_at = datetime.now()
                
                reports.append({
                    'id': file_id,
                    'filename': info['filename'],
                    'message_type': info.get('message_type', 'Unknown'),
                    'status': info.get('validation_status', 'UNKNOWN'),
                    'report_path': info.get('report_path', ''),
                    'corrected_path': info.get('corrected_path'),
                    'date': validated_at.strftime('%Y-%m-%d %H:%M:%S'),
                    'errors': info.get('errors', 0),
                    'warnings': info.get('warnings', 0)
                })
        print(f"DEBUG: Found {len(reports)} completed reports for this session")
    else:
        print("DEBUG: No session_id in session")
    
    return reports

@app.route('/')
def index():
    """Redirect to dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard showing all validation reports"""
    reports = get_sample_reports()
    
    # Check if API key is set
    has_api_key = 'api_key' in session
    
    return render_template('dashboard.html', 
                         reports=reports,
                         has_api_key=has_api_key,
                         total_files=len(reports),
                         passed_count=sum(1 for r in reports if r['status'] == 'PASSED'),
                         failed_count=sum(1 for r in reports if r['status'] == 'FAILED'))

@app.route('/set-api-key', methods=['POST'])
def set_api_key():
    """Store API key in session"""
    api_key = request.form.get('api_key')
    if api_key:
        session['api_key'] = api_key
        session.permanent = True  # Make session persistent
        return jsonify({'success': True, 'message': 'API key set successfully'})
    return jsonify({'success': False, 'message': 'API key required'}), 400

@app.route('/clear-api-key', methods=['POST'])
def clear_api_key():
    """Clear API key from session"""
    session.pop('api_key', None)
    return jsonify({'success': True, 'message': 'API key cleared'})

@app.route('/report/<report_id>')
def view_report(report_id):
    """View individual validation report"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    print(f"\nDEBUG view_report: Looking for report_id={report_id}")
    print(f"DEBUG view_report: Session ID: {session.get('session_id', 'NO SESSION')}")
    print(f"DEBUG view_report: Total items in processing_results: {len(processing_results)}")
    print(f"DEBUG view_report: Keys in processing_results: {list(processing_results.keys())}")
    
    reports = get_sample_reports()
    print(f"DEBUG view_report: get_sample_reports() returned {len(reports)} reports")
    for r in reports:
        print(f"  - Report ID: {r['id']}, filename: {r['filename']}")
    
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if not report:
        print(f"DEBUG view_report: Report {report_id} NOT FOUND in reports list")
        return "Report not found", 404
    
    print(f"DEBUG view_report: Found report: {report['filename']}")
    
    # Get markdown content from memory (stored during validation)
    if report_id in processing_results and 'report_content' in processing_results[report_id]:
        md_content = processing_results[report_id]['report_content']
        print(f"DEBUG view_report: Found report_content (length: {len(md_content)})")
    else:
        print(f"DEBUG view_report: report_content NOT FOUND for {report_id}")
        print(f"  - report_id in processing_results: {report_id in processing_results}")
        if report_id in processing_results:
            print(f"  - Keys in processing_results[{report_id}]: {list(processing_results[report_id].keys())}")
        return "Report content not found", 404
    
    # Convert to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    return render_template('report.html',
                         report=report,
                         html_content=html_content,
                         markdown_content=md_content)

@app.route('/report/<report_id>/pdf')
def export_pdf(report_id):
    """Export report as PDF using Playwright (browser-based, perfect emoji support)"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    reports = get_sample_reports()
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if not report:
        return "Report not found", 404
    
    # Read markdown content from memory (stored during validation)
    if report_id in processing_results and 'report_content' in processing_results[report_id]:
        md_content = processing_results[report_id]['report_content']
    else:
        return "Report content not found", 404
    
    # Convert to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Create styled HTML template (same as browser view)
    status_color = '#27ae60' if report['status'] == 'PASSED' else '#e74c3c'
    status_emoji = '✅' if report['status'] == 'PASSED' else '❌'
    
    html_template = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            @page {{
                margin: 2cm;
                size: A4;
            }}
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Arial, sans-serif;
                font-size: 11pt;
                line-height: 1.6;
                color: #2c3e50;
                margin: 0;
                padding: 20px;
            }}
            h1 {{
                color: #2c3e50;
                font-size: 20pt;
                border-bottom: 3px solid #3498db;
                padding-bottom: 10px;
                margin-bottom: 20px;
            }}
            h2 {{
                color: #34495e;
                font-size: 16pt;
                margin-top: 20px;
                margin-bottom: 10px;
                border-bottom: 2px solid #ecf0f1;
                padding-bottom: 5px;
            }}
            h3 {{
                color: #7f8c8d;
                font-size: 14pt;
                margin-top: 15px;
            }}
            h4 {{
                color: #95a5a6;
                font-size: 12pt;
            }}
            .metadata {{
                background: #f8f9fa;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
                border-left: 4px solid #3498db;
            }}
            .metadata p {{
                margin: 5px 0;
            }}
            .status {{
                color: {status_color};
                font-weight: bold;
            }}
            code {{
                background: #f4f4f4;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Courier New', Consolas, monospace;
                font-size: 10pt;
                color: #e74c3c;
            }}
            pre {{
                background: #2c3e50;
                color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
                border-left: 4px solid #3498db;
                font-size: 9pt;
            }}
            pre code {{
                background: none;
                color: #ecf0f1;
                padding: 0;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            th {{
                background-color: #3498db;
                color: white;
            }}
            hr {{
                border: none;
                border-top: 2px solid #ecf0f1;
                margin: 20px 0;
            }}
            .footer {{
                margin-top: 30px;
                padding-top: 15px;
                border-top: 1px solid #ddd;
                font-size: 9pt;
                color: #7f8c8d;
                text-align: center;
            }}
        </style>
    </head>
    <body>
        <h1>HL7 v2 Validation Report</h1>
        
        <div class="metadata">
            <p><strong>File:</strong> {report['filename']}</p>
            <p><strong>Message Type:</strong> {report['message_type']}</p>
            <p><strong>Date:</strong> {report['date']}</p>
            <p><strong>Status:</strong> <span class="status">{status_emoji} {report['status']}</span></p>
            <p><strong>Errors:</strong> {report['errors']}</p>
            <p><strong>Warnings:</strong> {report['warnings']}</p>
        </div>
        
        {html_content}
        
        <div class="footer">
            Generated by Gazelle HL7 v2 Validation Dashboard on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}
        </div>
    </body>
    </html>
    """
    
    # Generate PDF using Playwright (headless browser)
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_content(html_template)
        pdf_bytes = page.pdf(format='A4', print_background=True)
        browser.close()
    
    # Create response
    buffer = BytesIO(pdf_bytes)
    buffer.seek(0)
    
    return send_file(buffer,
                    as_attachment=True,
                    download_name=f"{report['filename']}_validation_report.pdf",
                    mimetype='application/pdf')

@app.route('/download/<report_id>/corrected')
def download_corrected(report_id):
    """Download corrected file"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    reports = get_sample_reports()
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if not report or not report['corrected_path']:
        return "Corrected file not found", 404
    
    return send_file(report['corrected_path'],
                    as_attachment=True,
                    download_name=f"{report['filename'].replace('.txt', '_CORRECTED.txt')}",
                    mimetype='text/plain')

@app.route('/auto-correct/<report_id>', methods=['POST'])
def retry_auto_correct(report_id):
    """Retry auto-correction on a failed validation"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    if report_id not in processing_results:
        return jsonify({'success': False, 'message': 'Report not found'}), 404
    
    file_info = processing_results[report_id]
    original_filepath = file_info['filepath']
    
    try:
        # Read original file as bytes
        with open(original_filepath, 'rb') as f:
            original_content = f.read()
        
        # Apply corrections
        corrector = HL7MessageCorrector()
        corrected_content, corrections_list = corrector.prepare_message(original_content, file_info['filename'])
        corrections_summary = corrector.get_corrections_summary()
        correction_report = corrector.get_correction_report()
        
        if corrections_summary['total_corrections'] == 0:
            return jsonify({
                'success': False,
                'message': 'No corrections could be applied automatically. Manual review required.'
            })
        
        # Save corrected file
        corrected_filepath = original_filepath.replace('.txt', '_CORRECTED.txt').replace('.xml', '_CORRECTED.xml')
        with open(corrected_filepath, 'wb') as f:
            f.write(corrected_content)
        
        # Update processing results
        processing_results[report_id]['corrected_path'] = corrected_filepath
        processing_results[report_id]['corrections_applied'] = corrections_summary
        processing_results[report_id]['correction_report'] = correction_report
        
        return jsonify({
            'success': True,
            'message': f"Successfully applied {corrections_summary['total_corrections']} corrections.",
            'corrections_applied': corrections_summary['total_corrections'],
            'critical_fixes': corrections_summary.get('critical_fixes', 0),
            'code_fixes': corrections_summary.get('code_fixes', 0),
            'field_insertions': corrections_summary.get('field_insertions', 0),
            'corrected_file': corrected_filepath
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Auto-correction failed: {str(e)}'
        }), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload-page')
def upload_page():
    """Upload page"""
    has_api_key = 'api_key' in session
    return render_template('upload.html', has_api_key=has_api_key)

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'message': 'Invalid file type. Only .txt and .xml allowed'}), 400
    
    # Generate unique ID for this upload
    file_id = str(uuid.uuid4())
    
    # Create session folder if needed
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    session_folder = os.path.join(UPLOAD_FOLDER, session['session_id'])
    os.makedirs(session_folder, exist_ok=True)
    
    # Save file
    filename = secure_filename(file.filename)
    filepath = os.path.join(session_folder, f"{file_id}_{filename}")
    file.save(filepath)
    
    # Store file info
    processing_results[file_id] = {
        'filename': filename,
        'filepath': filepath,
        'status': 'uploaded',
        'session_id': session['session_id']
    }
    
    return jsonify({
        'success': True,
        'file_id': file_id,
        'filename': filename
    })

@app.route('/validate/<file_id>', methods=['POST'])
def validate_file(file_id):
    """Validate uploaded file (without automatic correction)"""
    if file_id not in processing_results:
        return jsonify({'success': False, 'message': 'File not found'}), 404
    
    if 'api_key' not in session:
        return jsonify({'success': False, 'message': 'API key not set'}), 400
    
    file_info = processing_results[file_id]
    filepath = file_info['filepath']
    
    print(f"\nDEBUG: Starting validation for file_id={file_id}, filename={file_info['filename']}")
    print(f"DEBUG: Session ID: {session.get('session_id')}")
    
    # Update status
    processing_results[file_id]['status'] = 'validating'
    
    # Run validation using our validation tool
    try:
        # Create a temporary .env file with the API key in the project root
        temp_env = os.path.join(os.getcwd(), '.env.temp')
        
        with open(temp_env, 'w') as f:
            f.write(f"GAZELLE_API_KEY={session['api_key']}\n")
            f.write("VERIFY_SSL=True\n")
        
        # Temporarily rename original .env and use temp one
        original_env = os.path.join(os.getcwd(), '.env')
        backup_env = None
        if os.path.exists(original_env):
            backup_env = os.path.join(os.getcwd(), '.env.backup')
            os.rename(original_env, backup_env)
        os.rename(temp_env, original_env)
        
        try:
            # Run validation script with UTF-8 encoding to handle emojis
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'  # Force UTF-8 mode on Windows
            
            python_executable = sys.executable or shutil.which('python') or 'python'
            script_path = os.path.join(os.getcwd(), 'validate_with_verification.py')
            result = subprocess.run(
                [python_executable, script_path, filepath, '--warnings'],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=os.getcwd(),
                env=env,
                encoding='utf-8',
                errors='replace'
            )
        finally:
            # Restore original .env
            if os.path.exists(original_env):
                os.remove(original_env)
            if backup_env and os.path.exists(backup_env):
                os.rename(backup_env, original_env)
        
        # Parse output to get validation results
        # Combine stdout and stderr since error details might be in either
        output = result.stdout + "\n" + result.stderr
        stderr_output = result.stderr
        
        # DEBUG: Print to console what we captured
        print(f"\n{'='*80}")
        print(f"DEBUG: Validation subprocess for {file_info['filename']}")
        print(f"{'='*80}")
        print(f"Return code: {result.returncode}")
        print(f"STDOUT length: {len(result.stdout)} chars")
        print(f"STDERR length: {len(stderr_output)} chars")
        print(f"\nFull STDOUT:")
        print(result.stdout)
        print(f"\nFull STDERR:")
        print(stderr_output)
        print(f"{'='*80}\n")
        
        # Extract status (PASSED/FAILED) - use STDOUT only for parsing
        validation_output = result.stdout
        status = 'UNKNOWN'
        errors = 0
        warnings = 0
        report_url = ''
        oid = ''
        detected_message_type = None
        
        for line in validation_output.split('\n'):
            if 'Status:' in line:
                status_text = line.split('Status:')[1].strip()
                # Check for PASSED anywhere in the status (could be PASSED or DONE_PASSED)
                if 'PASSED' in status_text.upper():
                    status = 'PASSED'
                elif 'FAILED' in status_text.upper():
                    status = 'FAILED'
                else:
                    status = status_text
            elif 'VALIDATION PASSED' in line.upper():
                status = 'PASSED'
            elif 'VALIDATION FAILED' in line.upper():
                status = 'FAILED'
            elif 'Message Type:' in line:
                # Extract message type from validation output
                detected_message_type = line.split('Message Type:')[1].strip()
            elif 'Errors:' in line and 'MANDATORY:' in line:
                try:
                    errors = int(line.split('MANDATORY:')[1].split(')')[0].strip())
                except:
                    pass
            elif 'Warnings:' in line and 'Warning #' not in line:
                try:
                    warnings = int(line.split('Warnings:')[1].strip())
                except:
                    pass
            elif 'Report:' in line and 'http' in line:
                report_url = line.split('Report:')[1].strip()
                # Extract OID from URL
                if 'oid=' in report_url:
                    oid = report_url.split('oid=')[1].split('&')[0]
            elif 'OID:' in line:
                oid = line.split('OID:')[1].strip()
        
        # If we have 0 errors and 0 warnings and status is still UNKNOWN, default to PASSED
        if status == 'UNKNOWN' and errors == 0 and warnings == 0:
            status = 'PASSED'
        elif status == 'UNKNOWN':
            status = 'FAILED'
        
        # Fetch detailed error information from Gazelle XML report
        detailed_errors, detailed_warnings, xml_report = fetch_and_parse_gazelle_report(oid, session['api_key']) if oid else (None, None, None)
        
        # Create report markdown with detailed format (matching last night's reports)
        report_content = ""  # Store content in memory
        
        # Use detected message type from validation output, or try to detect from filename as fallback
        message_type = 'Unknown'
        message_type_display = 'Unknown'
        
        if detected_message_type:
            message_type = detected_message_type.replace('^', '_')
            # Map to friendly display names
            if detected_message_type == 'ADT^A01':
                message_type_display = 'ADT^A01 (Patient Admission)'
            elif detected_message_type == 'ADT^A03':
                message_type_display = 'ADT^A03 (Patient Discharge)'
            elif detected_message_type == 'SIU^S12':
                message_type_display = 'SIU^S12 (Appointment Notification)'
            elif detected_message_type == 'SIU^S13':
                message_type_display = 'SIU^S13 (Appointment Rescheduling)'
            elif detected_message_type == 'REF^I12':
                message_type_display = 'REF^I12 (Patient Referral)'
            elif detected_message_type == 'RRI^I12':
                message_type_display = 'RRI^I12 (Referral Response)'
            elif detected_message_type == 'ORU^R01':
                message_type_display = 'ORU^R01 (Laboratory Results)'
            else:
                message_type_display = detected_message_type
        elif 'SIU' in file_info['filename']:
            message_type = 'SIU_S12'
            message_type_display = 'SIU^S12 (Appointment Notification)'
        elif 'ORU' in file_info['filename']:
            message_type = 'ORU_R01'
            message_type_display = 'ORU^R01 (Laboratory Results)'
        elif 'ADT' in file_info['filename']:
            message_type = 'ADT_A01'
            message_type_display = 'ADT^A01 (Patient Admission)'
        
        # Generate detailed markdown report (stored in memory)
        report_content += f"# {file_info['filename']} - ERROR ANALYSIS AND CORRECTIONS\n\n"
        
        status_emoji = "✅" if status == "PASSED" else "❌"
        report_content += f"**Validation Status:** {status_emoji} {status}  \n"
        report_content += f"**Message Type:** {message_type_display}  \n"
        report_content += f"**Validator:** Gazelle HL7v2.x validator (OID: 1.3.6.1.4.1.12559.11.35.10.1.12)  \n"
        report_content += f"**Validation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n"
        
        # Add auto-correction summary if it exists (from manual retry)
        corrections_summary = processing_results[file_id].get('corrections_applied', {})
        correction_report = processing_results[file_id].get('correction_report', '')
        if corrections_summary.get('total_corrections', 0) > 0:
            report_content += f"**Auto-Corrections Applied:** {corrections_summary['total_corrections']} fixes  \n"
            report_content += f"  - Critical fixes: {corrections_summary.get('critical_fixes', 0)}  \n"
            report_content += f"  - Code corrections: {corrections_summary.get('code_fixes', 0)}  \n"
            report_content += f"  - Field insertions: {corrections_summary.get('field_insertions', 0)}  \n\n"
        
        # Calculate passed checks
        total_checks = errors + warnings + 50  # Approximate
        passed = total_checks - errors - warnings
        report_content += f"**Validation Summary:** {errors} Errors, {warnings} Warnings, {passed} Passed\n\n"
        
        if report_url:
            report_content += f"**Full Gazelle Report:** [{report_url}]({report_url})\n\n"
        
        report_content += "---\n\n"
        
        # Add detailed auto-correction report if corrections were applied
        if corrections_summary.get('total_corrections', 0) > 0:
            report_content += "## 🤖 AUTOMATIC CORRECTIONS APPLIED\n\n"
            report_content += correction_report
            report_content += "\n\n---\n\n"
        
        # Use detailed errors if available, otherwise parse from output
        if detailed_errors and len(detailed_errors) > 0:
            report_content += "## 📋 ERRORS FOUND (From Gazelle Validation Report)\n\n"
            for i, error in enumerate(detailed_errors, 1):
                report_content += f"### ❌ ERROR #{i}: {error['type']}\n\n"
                report_content += f"**Location:** `{error['location']}`  \n"
                report_content += f"**Constraint Description:** {error['description']}  \n"
                report_content += f"**Priority:** {error['priority']}  \n"
                report_content += f"**Constraint Type:** {error['type']}  \n\n"
                report_content += "#### Plain Language Explanation\n"
                report_content += f"{error['description']}\n\n"
                report_content += "#### The Fix\n"
                report_content += "Review the constraint description above and correct the value at the specified location.\n\n"
                report_content += "---\n\n"
        elif errors > 0:
            report_content += "## 📋 ERRORS FOUND\n\n"
            report_content += "⚠️ *Detailed error information not available. Please check the full Gazelle report above.*\n\n"
            lines = output.split('\n')
            in_error_section = False
            for i, line in enumerate(lines):
                if 'Error #' in line or 'ERROR' in line.upper():
                    in_error_section = True
                    report_content += f"\n{line}\n"
                elif in_error_section:
                    if line.strip():
                        report_content += f"{line}\n"
                    else:
                        in_error_section = False
            report_content += "\n---\n\n"
        
        # Use detailed warnings if available
        if detailed_warnings and len(detailed_warnings) > 0:
            report_content += "## ⚠️ WARNINGS FOUND (From Gazelle Validation Report)\n\n"
            for i, warning in enumerate(detailed_warnings, 1):
                report_content += f"### ⚠️ WARNING #{i}: {warning['type']}\n\n"
                report_content += f"**Location:** `{warning['location']}`  \n"
                report_content += f"**Constraint Description:** {warning['description']}  \n"
                report_content += f"**Priority:** {warning['priority']}  \n"
                report_content += f"**Constraint Type:** {warning['type']}  \n\n"
                report_content += "#### Plain Language Explanation\n"
                report_content += f"{warning['description']}\n\n"
                report_content += "This is a recommended improvement but not strictly required.\n\n"
                report_content += "---\n\n"
        elif warnings > 0:
            report_content += "## ⚠️ WARNINGS FOUND\n\n"
            report_content += "⚠️ *Detailed warning information not available. Please check the full Gazelle report above.*\n\n"
            lines = output.split('\n')
            in_warning_section = False
            for i, line in enumerate(lines):
                if 'Warning #' in line or 'WARNING' in line.upper():
                    in_warning_section = True
                    report_content += f"\n{line}\n"
                elif in_warning_section:
                    if line.strip():
                        report_content += f"{line}\n"
                    else:
                        in_warning_section = False
            report_content += "\n---\n\n"
        
        # Full validation output section
        report_content += "## 📄 COMPLETE VALIDATION OUTPUT\n\n"
        report_content += "```\n"
        report_content += output
        report_content += "\n```\n\n"
        
        # If validation failed and we have detailed errors, attempt auto-correction
        auto_correction_attempted = False
        corrected_file_path = None
        
        if status == "FAILED" and detailed_errors and len(detailed_errors) > 0:
            report_content += "## 🤖 ATTEMPTING AUTOMATIC CORRECTION\n\n"
            report_content += "Analyzing errors and attempting to apply automatic fixes...\n\n"
            
            # Attempt auto-correction
            try:
                from auto_correct import auto_correct_and_validate
                correction_result = auto_correct_and_validate(filepath, detailed_errors, session['api_key'])
                
                if correction_result['success']:
                    auto_correction_attempted = True
                    corrected_file_path = correction_result['corrected_file']
                    
                    report_content += "### ✅ Automatic Corrections Applied\n\n"
                    report_content += correction_result['correction_report']
                    report_content += "\n\n"
                    report_content += f"**Corrected file saved to:** `{corrected_file_path}`\n\n"
                    report_content += "**Note:** The corrected file needs to be re-validated. Upload it again to verify it passes.\n\n"
                else:
                    report_content += "### ⚠️ Automatic Correction Not Possible\n\n"
                    report_content += f"Reason: {correction_result.get('error', 'Unknown error')}\n\n"
                    report_content += "Manual correction required. Please review the errors above.\n\n"
            
            except Exception as e:
                report_content += f"### ❌ Auto-Correction Error\n\n"
                report_content += f"Error: {str(e)}\n\n"
            
            report_content += "---\n\n"
        
        if status == "PASSED":
            report_content += "## ✅ VALIDATION SUCCESSFUL\n\n"
            report_content += "This message has passed all mandatory validation checks and is ready for submission.\n\n"
        else:
            report_content += "## 🔧 NEXT STEPS\n\n"
            if auto_correction_attempted:
                report_content += "1. Download the auto-corrected file below\n"
                report_content += "2. Re-upload and validate the corrected file\n"
                report_content += "3. If errors persist, manually review and correct\n\n"
            else:
                report_content += "1. Review each error above\n"
                report_content += "2. Correct the issues in your HL7 message\n"
                report_content += "3. Re-upload and validate the corrected message\n"
                report_content += "4. Download the corrected version once validation passes\n\n"
        
        report_content += "---\n\n"
        report_content += f"*Report generated by Gazelle HL7 Validator Dashboard on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n"
        
        # Update processing results - store report content in memory instead of disk
        processing_results[file_id].update({
            'status': 'completed',
            'validation_status': status,
            'errors': errors,
            'warnings': warnings,
            'report_content': report_content,  # Store markdown content in memory
            'report_url': report_url,
            'message_type': message_type,
            'validated_at': datetime.now().isoformat(),
            'corrected_path': corrected_file_path if corrected_file_path else None
        })
        
        # Save to temp file so results persist across dyno restarts
        save_processing_results()
        
        print(f"DEBUG: Validation completed for file_id={file_id}")
        print(f"DEBUG: Status={status}, Errors={errors}, Warnings={warnings}")
        print(f"DEBUG: processing_results[{file_id}] status is now: {processing_results[file_id]['status']}")
        
        return jsonify({
            'success': True,
            'status': status,
            'errors': errors,
            'warnings': warnings,
            'report_url': report_url
        })
        
    except subprocess.TimeoutExpired:
        processing_results[file_id]['status'] = 'timeout'
        save_processing_results()
        return jsonify({'success': False, 'message': 'Validation timeout'}), 500
    except Exception as e:
        processing_results[file_id]['status'] = 'error'
        save_processing_results()
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
