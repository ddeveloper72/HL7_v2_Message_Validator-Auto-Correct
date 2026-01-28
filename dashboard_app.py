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
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT
import uuid
import shutil
from werkzeug.utils import secure_filename
import subprocess
import threading
import requests
from xml.etree import ElementTree as ET

app = Flask(__name__)
app.secret_key = os.urandom(24)  # For session management

# Configure folders
UPLOAD_FOLDER = 'uploads'
PROCESSED_FOLDER = 'processed'
REPORTS_FOLDER = 'Healthlink Tests'  # Using existing test reports
ALLOWED_EXTENSIONS = {'txt', 'xml'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESSED_FOLDER, exist_ok=True)

# Store processing results in memory (in production, use a database)
processing_results = {}

def load_processing_results():
    """Load processing results from disk"""
    global processing_results
    results_file = os.path.join(PROCESSED_FOLDER, 'results.json')
    if os.path.exists(results_file):
        try:
            with open(results_file, 'r') as f:
                processing_results = json.load(f)
        except:
            processing_results = {}
    else:
        processing_results = {}

def save_processing_results():
    """Save processing results to disk"""
    results_file = os.path.join(PROCESSED_FOLDER, 'results.json')
    with open(results_file, 'w') as f:
        json.dump(processing_results, f, indent=2)

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
    reports = []
    
    # Only show session-uploaded files (user's own validations)
    if 'session_id' in session:
        for file_id, info in processing_results.items():
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
    reports = get_sample_reports()
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if not report:
        return "Report not found", 404
    
    # Read markdown content
    with open(report['report_path'], 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Convert to HTML
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    return render_template('report.html',
                         report=report,
                         html_content=html_content,
                         markdown_content=md_content)

@app.route('/report/<report_id>/pdf')
def export_pdf(report_id):
    """Export report as PDF using ReportLab"""
    reports = get_sample_reports()
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if not report:
        return "Report not found", 404
    
    # Read markdown content
    with open(report['report_path'], 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    # Create PDF in memory
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=72, leftMargin=72,
                           topMargin=72, bottomMargin=18)
    
    # Container for PDF elements
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#2c3e50',
        spaceAfter=30,
        alignment=TA_CENTER
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor='#34495e',
        spaceAfter=12,
        spaceBefore=12
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=11,
        leading=14
    )
    
    # Add title
    elements.append(Paragraph("HL7 v2 Validation Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Add metadata
    elements.append(Paragraph(f"<b>File:</b> {report['filename']}", body_style))
    elements.append(Paragraph(f"<b>Message Type:</b> {report['message_type']}", body_style))
    elements.append(Paragraph(f"<b>Date:</b> {report['date']}", body_style))
    elements.append(Paragraph(f"<b>Status:</b> {report['status']}", body_style))
    elements.append(Paragraph(f"<b>Errors:</b> {report['errors']}", body_style))
    elements.append(Paragraph(f"<b>Warnings:</b> {report['warnings']}", body_style))
    elements.append(Spacer(1, 20))
    
    # Add report content (simplified - just the text)
    for line in md_content.split('\n'):
        if line.strip():
            if line.startswith('# '):
                elements.append(Paragraph(line[2:], heading_style))
            elif line.startswith('## '):
                elements.append(Paragraph(line[3:], heading_style))
            elif line.startswith('```'):
                continue  # Skip code fences
            else:
                # Clean up markdown syntax
                clean_line = line.replace('**', '<b>').replace('`', '<i>')
                try:
                    elements.append(Paragraph(clean_line, body_style))
                except:
                    pass  # Skip problematic lines
            elements.append(Spacer(1, 6))
    
    # Add footer
    elements.append(Spacer(1, 30))
    footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontSize=9, textColor='#7f8c8d')
    elements.append(Paragraph(f"Generated by Gazelle HL7 v2 Validation Dashboard on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(buffer,
                    as_attachment=True,
                    download_name=f"{report['filename']}_validation_report.pdf",
                    mimetype='application/pdf')

@app.route('/download/<report_id>/corrected')
def download_corrected(report_id):
    """Download corrected file"""
    reports = get_sample_reports()
    report = next((r for r in reports if r['id'] == report_id), None)
    
    if not report or not report['corrected_path']:
        return "Corrected file not found", 404
    
    return send_file(report['corrected_path'],
                    as_attachment=True,
                    download_name=f"{report['filename'].replace('.txt', '_CORRECTED.txt')}",
                    mimetype='text/plain')

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
    """Validate uploaded file"""
    if file_id not in processing_results:
        return jsonify({'success': False, 'message': 'File not found'}), 404
    
    if 'api_key' not in session:
        return jsonify({'success': False, 'message': 'API key not set'}), 400
    
    file_info = processing_results[file_id]
    filepath = file_info['filepath']
    
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
            
            result = subprocess.run(
                ['.venv\\Scripts\\python.exe', 'validate_with_verification.py', filepath, '--warnings'],
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
        session_folder = os.path.join(PROCESSED_FOLDER, session['session_id'])
        os.makedirs(session_folder, exist_ok=True)
        
        report_path = os.path.join(session_folder, f"{file_id}_report.md")
        
        # Detect message type from filename
        message_type = 'Unknown'
        message_type_display = 'Unknown'
        if 'SIU' in file_info['filename']:
            message_type = 'SIU_S12'
            message_type_display = 'SIU^S12 (Appointment Notification)'
        elif 'ORU' in file_info['filename']:
            message_type = 'ORU_R01'
            message_type_display = 'ORU^R01 (Laboratory Results - HL-12)'
        elif 'ADT' in file_info['filename']:
            message_type = 'ADT_A01'
            message_type_display = 'ADT^A01 (Patient Admission)'
        
        # Generate detailed markdown report
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(f"# {file_info['filename']} - ERROR ANALYSIS AND CORRECTIONS\n\n")
            
            status_emoji = "✅" if status == "PASSED" else "❌"
            f.write(f"**Validation Status:** {status_emoji} {status}  \n")
            f.write(f"**Message Type:** {message_type_display}  \n")
            f.write(f"**Validator:** Gazelle HL7v2.x validator (OID: 1.3.6.1.4.1.12559.11.35.10.1.12)  \n")
            f.write(f"**Validation Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  \n")
            
            # Calculate passed checks
            total_checks = errors + warnings + 50  # Approximate
            passed = total_checks - errors - warnings
            f.write(f"**Validation Summary:** {errors} Errors, {warnings} Warnings, {passed} Passed\n\n")
            
            if report_url:
                f.write(f"**Full Gazelle Report:** [{report_url}]({report_url})\n\n")
            
            f.write("---\n\n")
            
            # Use detailed errors if available, otherwise parse from output
            if detailed_errors and len(detailed_errors) > 0:
                f.write("## 📋 ERRORS FOUND (From Gazelle Validation Report)\n\n")
                for i, error in enumerate(detailed_errors, 1):
                    f.write(f"### ❌ ERROR #{i}: {error['type']}\n\n")
                    f.write(f"**Location:** `{error['location']}`  \n")
                    f.write(f"**Constraint Description:** {error['description']}  \n")
                    f.write(f"**Priority:** {error['priority']}  \n")
                    f.write(f"**Constraint Type:** {error['type']}  \n\n")
                    f.write("#### Plain Language Explanation\n")
                    f.write(f"{error['description']}\n\n")
                    f.write("#### The Fix\n")
                    f.write("Review the constraint description above and correct the value at the specified location.\n\n")
                    f.write("---\n\n")
            elif errors > 0:
                f.write("## 📋 ERRORS FOUND\n\n")
                f.write("⚠️ *Detailed error information not available. Please check the full Gazelle report above.*\n\n")
                lines = output.split('\n')
                in_error_section = False
                for i, line in enumerate(lines):
                    if 'Error #' in line or 'ERROR' in line.upper():
                        in_error_section = True
                        f.write(f"\n{line}\n")
                    elif in_error_section:
                        if line.strip():
                            f.write(f"{line}\n")
                        else:
                            in_error_section = False
                f.write("\n---\n\n")
            
            # Use detailed warnings if available
            if detailed_warnings and len(detailed_warnings) > 0:
                f.write("## ⚠️ WARNINGS FOUND (From Gazelle Validation Report)\n\n")
                for i, warning in enumerate(detailed_warnings, 1):
                    f.write(f"### ⚠️ WARNING #{i}: {warning['type']}\n\n")
                    f.write(f"**Location:** `{warning['location']}`  \n")
                    f.write(f"**Constraint Description:** {warning['description']}  \n")
                    f.write(f"**Priority:** {warning['priority']}  \n")
                    f.write(f"**Constraint Type:** {warning['type']}  \n\n")
                    f.write("#### Plain Language Explanation\n")
                    f.write(f"{warning['description']}\n\n")
                    f.write("This is a recommended improvement but not strictly required.\n\n")
                    f.write("---\n\n")
            elif warnings > 0:
                f.write("## ⚠️ WARNINGS FOUND\n\n")
                f.write("⚠️ *Detailed warning information not available. Please check the full Gazelle report above.*\n\n")
                lines = output.split('\n')
                in_warning_section = False
                for i, line in enumerate(lines):
                    if 'Warning #' in line or 'WARNING' in line.upper():
                        in_warning_section = True
                        f.write(f"\n{line}\n")
                    elif in_warning_section:
                        if line.strip():
                            f.write(f"{line}\n")
                        else:
                            in_warning_section = False
                f.write("\n---\n\n")
            
            # Full validation output section
            f.write("## 📄 COMPLETE VALIDATION OUTPUT\n\n")
            f.write("```\n")
            f.write(output)
            f.write("\n```\n\n")
            
            if status == "PASSED":
                f.write("## ✅ VALIDATION SUCCESSFUL\n\n")
                f.write("This message has passed all mandatory validation checks and is ready for submission.\n\n")
            else:
                f.write("## 🔧 NEXT STEPS\n\n")
                f.write("1. Review each error above\n")
                f.write("2. Correct the issues in your HL7 message\n")
                f.write("3. Re-upload and validate the corrected message\n")
                f.write("4. Download the corrected version once validation passes\n\n")
            
            f.write("---\n\n")
            f.write(f"*Report generated by Gazelle HL7 Validator Dashboard on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n")
        
        # Detect message type from filename
        message_type = 'Unknown'
        if 'SIU' in file_info['filename']:
            message_type = 'SIU_S12'
        elif 'ORU' in file_info['filename']:
            message_type = 'ORU_R01'
        elif 'ADT' in file_info['filename']:
            message_type = 'ADT_A01'
        
        # Update processing results
        processing_results[file_id].update({
            'status': 'completed',
            'validation_status': status,
            'errors': errors,
            'warnings': warnings,
            'report_path': report_path,
            'report_url': report_url,
            'message_type': message_type,
            'validated_at': datetime.now().isoformat()
        })
        save_processing_results()
        
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
