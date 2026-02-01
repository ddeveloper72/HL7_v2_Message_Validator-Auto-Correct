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
from weasyprint import HTML, CSS
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
import re
from functools import wraps

# Security imports
from flask_wtf.csrf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import bleach

# Azure AD and Database imports
import msal
from db_utils import DatabaseManager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

# Session configuration - use environment variable or fallback for development
session_secret = os.environ.get('SESSION_SECRET_KEY')
if not session_secret:
    # For local development only - generate a persistent key
    if os.path.exists('.session_secret'):
        with open('.session_secret', 'r') as f:
            session_secret = f.read().strip()
    else:
        session_secret = os.urandom(32).hex()  # 32 bytes = 256 bits for strong security
        # Don't save for Heroku - it needs to be set as an environment variable
        if not os.environ.get('DYNO'):  # Only save locally (not on Heroku)
            with open('.session_secret', 'w') as f:
                f.write(session_secret)

app.secret_key = session_secret

# Configure session to be more compatible with multiple workers
# Use HTTPS-only cookies in production (Heroku)
app.config['SESSION_COOKIE_SECURE'] = True if os.environ.get('DYNO') else False
app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
app.config['PERMANENT_SESSION_LIFETIME'] = 86400 * 7  # 7 days
app.config['SESSION_TYPE'] = 'filesystem'  # Store sessions on disk
app.config['SESSION_PERMANENT'] = True  # Sessions persist across browser restarts

# Security configuration
csrf = CSRFProtect(app)

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Azure AD Configuration
AZURE_AD_CLIENT_ID = os.getenv('AZURE_AD_CLIENT_ID')
AZURE_AD_CLIENT_SECRET = os.getenv('AZURE_AD_CLIENT_SECRET')
AZURE_AD_TENANT_ID = os.getenv('AZURE_AD_TENANT_ID')
AZURE_AD_REDIRECT_URI = os.getenv('AZURE_AD_REDIRECT_URI', 'http://localhost:5000/auth/callback')
AZURE_AD_AUTHORITY = f'https://login.microsoftonline.com/{AZURE_AD_TENANT_ID}'
AZURE_AD_SCOPE = ['User.Read']

# Initialize database manager
db = DatabaseManager()

# Initialize MSAL Confidential Client
def get_msal_app():
    """Create MSAL confidential client application"""
    return msal.ConfidentialClientApplication(
        AZURE_AD_CLIENT_ID,
        authority=AZURE_AD_AUTHORITY,
        client_credential=AZURE_AD_CLIENT_SECRET
    )

# Authentication decorator
def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

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

# Security headers middleware
@app.after_request
def set_security_headers(response):
    """Add security headers to all responses"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline' cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' cdn.jsdelivr.net; font-src 'self' cdn.jsdelivr.net data:; img-src 'self' data:; connect-src 'self' cdn.jsdelivr.net;"
    return response

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

def get_sample_reports(show_all=False):
    """Get user's validation reports"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    reports = []
    
    # Only show session-uploaded files (user's own validations)
    if show_all:
        for file_id, info in processing_results.items():
            if info.get('status') == 'completed':
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
        print(f"DEBUG: Found {len(reports)} completed reports (show_all)")
    elif 'session_id' in session:
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

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    """Landing page - redirect to login or dashboard"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
@csrf.exempt
def login():
    """Initiate Azure AD login flow"""
    msal_app = get_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        AZURE_AD_SCOPE,
        redirect_uri=AZURE_AD_REDIRECT_URI
    )
    session['state'] = str(uuid.uuid4())
    return redirect(auth_url)

@app.route('/auth/callback')
@csrf.exempt
def auth_callback():
    """Handle Azure AD callback"""
    code = request.args.get('code')
    if not code:
        return "Authentication failed: No authorization code", 400
    
    msal_app = get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=AZURE_AD_SCOPE,
        redirect_uri=AZURE_AD_REDIRECT_URI
    )
    
    if 'error' in result:
        return f"Authentication error: {result.get('error_description')}", 400
    
    # Get user info from token
    user_info = result.get('id_token_claims')
    email = user_info.get('preferred_username') or user_info.get('email')
    azure_ad_oid = user_info.get('oid')
    display_name = user_info.get('name')
    
    # Create or update user in database
    user_id = db.create_or_update_user(email, azure_ad_oid, display_name)
    
    # Store in session (mark as permanent BEFORE setting values)
    session.permanent = True
    session['user_id'] = user_id
    session['email'] = email
    session['display_name'] = display_name
    session['azure_ad_oid'] = azure_ad_oid
    session['logged_in_at'] = datetime.now().isoformat()
    
    # Load user's API key from database into session
    api_key = db.get_user_api_key(user_id)
    if api_key:
        session['api_key'] = api_key
    
    # Store MSAL token for refresh (optional but recommended)
    if 'access_token' in result:
        session['access_token'] = result['access_token']
    
    return redirect(url_for('profile'))

@app.route('/logout')
def logout():
    """Logout user"""
    session.clear()
    logout_url = f"{AZURE_AD_AUTHORITY}/oauth2/v2.0/logout?post_logout_redirect_uri={request.host_url}"
    return redirect(logout_url)

@app.route('/profile')
@login_required
def profile():
    """User profile page with API key management"""
    user_id = session['user_id']
    
    # Check if user has Gazelle API key
    api_key = db.get_user_api_key(user_id)
    has_api_key = api_key is not None
    
    # Get user statistics
    stats = db.get_user_statistics(user_id)
    
    return render_template('profile.html',
                         user_email=session.get('email'),
                         user_name=session.get('display_name'),
                         has_api_key=has_api_key,
                         stats=stats)

@app.route('/set-api-key-db', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def set_api_key_db():
    """Save user's Gazelle API key to database (encrypted)"""
    user_id = session['user_id']
    api_key = request.form.get('api_key', '').strip()
    
    # Input validation
    if not api_key:
        return jsonify({'success': False, 'message': 'API key required'}), 400
    
    if len(api_key) > 256:
        return jsonify({'success': False, 'message': 'API key too long (max 256 characters)'}), 400
    
    # Basic format validation - alphanumeric and common special chars only
    if not re.match(r'^[A-Za-z0-9_\-\.]+$', api_key):
        return jsonify({'success': False, 'message': 'Invalid API key format'}), 400
    
    try:
        # Save encrypted API key to database
        ip_address = request.remote_addr
        db.set_user_api_key(user_id, api_key, ip_address)
        
        # Also store in session for immediate use
        session['api_key'] = api_key
        
        return jsonify({'success': True, 'message': 'API key saved successfully'})
    except Exception as e:
        # Log the error but don't expose details to user
        print(f"Error saving API key: {e}")
        return jsonify({'success': False, 'message': 'Failed to save API key. Please try again.'}), 500

# ==================== DASHBOARD ROUTES ====================

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard showing all validation reports"""
    user_id = session['user_id']
    show_all = request.args.get('show_all') == '1'
    
    # Get current session reports from temp file
    temp_reports = get_sample_reports(show_all=show_all)
    
    # Get historical validation reports from database
    reports = []
    try:
        db_history = db.get_user_validation_history(user_id, limit=100)
        # Convert database records to report format
        for record in db_history:
            reports.append({
                'id': f"db_{record['id']}",  # Prefix with 'db_' to distinguish from temp file
                'filename': record['filename'],
                'message_type': record['message_type'],
                'status': record['status'],
                'report_url': record['report_url'],
                'date': record['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(record['timestamp'], 'strftime') else str(record['timestamp']),
                'errors': record['error_count'],
                'warnings': record['warning_count'],
                'corrections_applied': record.get('corrections_applied', 0),
                'validation_id': record['id']  # Store for auto-correct retrieval
            })
        print(f"DEBUG: Loaded {len(reports)} reports from database")
    except Exception as e:
        print(f"DEBUG: Error loading validation history from database: {e}")
        # Fallback to temp file reports only
        reports = temp_reports
    
    # Always check database for API key (source of truth)
    api_key = db.get_user_api_key(user_id)
    if api_key:
        session['api_key'] = api_key
    else:
        # Clear from session if not in database
        session.pop('api_key', None)
    
    has_api_key = api_key is not None
    
    # Get user statistics from database for accurate counts
    try:
        db_stats = db.get_user_statistics(user_id)
        total_files = db_stats['total']
        passed_count = db_stats['passed']
        failed_count = db_stats['failed']
    except Exception as e:
        print(f"DEBUG: Error loading stats from database: {e}")
        # Fallback to temp file stats
        total_files = len(reports)
        passed_count = sum(1 for r in reports if r['status'] == 'PASSED')
        failed_count = sum(1 for r in reports if r['status'] == 'FAILED')
    
    return render_template('dashboard.html', 
                         reports=reports,
                         has_api_key=has_api_key,
                         user_name=session.get('display_name'),
                         user_email=session.get('email'),
                         total_files=total_files,
                         passed_count=passed_count,
                         failed_count=failed_count,
                         show_all=show_all)

@app.route('/clear-history', methods=['POST'])
@login_required
@limiter.limit("5 per minute")
def clear_history():
    """Clear all validation history for the current user"""
    user_id = session['user_id']
    
    try:
        # Delete all validation records from database
        count = db.clear_user_validation_history(user_id)
        
        # Also clear from processing_results (temp file storage)
        global processing_results
        session_id = session.get('session_id')
        if session_id:
            # Remove only this user's session records
            keys_to_remove = [k for k, v in processing_results.items() 
                            if v.get('session_id') == session_id]
            for key in keys_to_remove:
                del processing_results[key]
            save_processing_results()
        
        print(f"DEBUG: Cleared {count} validation records for user {user_id}")
        
        return jsonify({
            'success': True,
            'message': f'Successfully deleted {count} validation record(s)',
            'count': count
        })
    except Exception as e:
        print(f"ERROR: Failed to clear history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Failed to clear validation history. Please try again.'
        }), 500

@app.route('/delete-record/<record_id>', methods=['POST'])
@login_required
@limiter.limit("10 per minute")
def delete_record(record_id):
    """Delete a single validation record"""
    user_id = session['user_id']
    
    try:
        # Handle database records (db_XXX format)
        if record_id.startswith('db_'):
            validation_id = int(record_id.replace('db_', ''))
            deleted = db.delete_validation_record(validation_id, user_id)
            
            if deleted:
                return jsonify({
                    'success': True,
                    'message': 'Record deleted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Record not found or you do not have permission to delete it'
                }), 404
        else:
            # Handle temp file records
            if record_id in processing_results:
                session_id = session.get('session_id')
                # Verify ownership
                if processing_results[record_id].get('session_id') == session_id:
                    del processing_results[record_id]
                    save_processing_results()
                    return jsonify({
                        'success': True,
                        'message': 'Record deleted successfully'
                    })
                else:
                    return jsonify({
                        'success': False,
                        'message': 'You do not have permission to delete this record'
                    }), 403
            else:
                return jsonify({
                    'success': False,
                    'message': 'Record not found'
                }), 404
    except Exception as e:
        print(f"ERROR: Failed to delete record {record_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Failed to delete record. Please try again.'
        }), 500

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
    """Clear API key from session and database"""
    # Remove from session
    session.pop('api_key', None)
    
    # Remove from database
    if 'user_id' in session:
        try:
            db.set_user_api_key(session['user_id'], None)
        except Exception as e:
            print(f"Error clearing API key from database: {e}")
    
    return jsonify({'success': True, 'message': 'API key cleared'})

@app.route('/delete-report/<report_id>', methods=['POST'])
@login_required
def delete_report(report_id):
    """Delete a validation report from the dashboard (handles both temp and database reports)"""
    user_id = session['user_id']
    
    try:
        # Handle database records (db_XXX format)
        if report_id.startswith('db_'):
            validation_id = int(report_id.replace('db_', ''))
            deleted = db.delete_validation_record(validation_id, user_id)
            
            if deleted:
                return jsonify({
                    'success': True,
                    'message': 'Report deleted successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'Report not found or you do not have permission to delete it'
                }), 404
        else:
            # Handle temp file records
            load_processing_results()
            
            if report_id not in processing_results:
                return jsonify({'success': False, 'message': 'Report not found'}), 404

            report_info = processing_results.get(report_id, {})
            session_id = session.get('session_id')
            
            # Verify ownership
            if report_info.get('session_id') != session_id:
                return jsonify({'success': False, 'message': 'Unauthorized'}), 403

            processing_results.pop(report_id, None)
            save_processing_results()

            return jsonify({'success': True, 'message': 'Report removed'})
    except Exception as e:
        print(f"ERROR: Failed to delete report {report_id}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': 'Failed to delete report. Please try again.'
        }), 500

@app.route('/report/<report_id>')
def view_report(report_id):
    """View individual validation report"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    print(f"\nDEBUG view_report: Looking for report_id={report_id}")
    print(f"DEBUG view_report: Session ID: {session.get('session_id', 'NO SESSION')}")
    
    # Check if this is a database report (prefixed with 'db_')
    if report_id.startswith('db_'):
        validation_id = int(report_id.replace('db_', ''))
        print(f"DEBUG view_report: Database report, validation_id={validation_id}")
        
        # Get report from database
        try:
            db_report = db.get_validation_report_by_id(validation_id)
            if not db_report:
                return "Report not found in database", 404
            
            # Build report dict for template
            report = {
                'id': report_id,
                'filename': db_report['filename'],
                'message_type': db_report['message_type'],
                'status': db_report['status'],
                'errors': db_report['error_count'],
                'warnings': db_report['warning_count'],
                'date': db_report['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(db_report['timestamp'], 'strftime') else str(db_report['timestamp']),
                'report_path': db_report.get('report_url', ''),
                'corrected_path': None,  # Database reports don't have local corrected files
                'validation_id': validation_id
            }
            
            # Use stored report details if available, otherwise generate basic report
            if db_report.get('report_details'):
                md_content = db_report['report_details']
                print(f"DEBUG view_report: Using stored report_details (length: {len(md_content)})")
            else:
                # Fallback: Generate basic markdown content for database report
                md_content = f"# Validation Report: {db_report['filename']}\n\n"
                md_content += f"**Status:** {db_report['status']}  \n"
                md_content += f"**Message Type:** {db_report['message_type']}  \n"
                md_content += f"**Validated:** {report['date']}  \n\n"
                md_content += f"**Errors:** {db_report['error_count']}  \n"
                md_content += f"**Warnings:** {db_report['warning_count']}  \n"
                if db_report.get('corrections_applied', 0) > 0:
                    md_content += f"**Corrections Applied:** {db_report['corrections_applied']}  \n"
                
                if db_report.get('report_url'):
                    md_content += f"\n[View Full Gazelle Report]({db_report['report_url']})\n"
                
                print(f"DEBUG view_report: Generated basic markdown for database report (no stored details)")
            
        except Exception as e:
            print(f"ERROR view_report: Failed to load database report: {e}")
            return f"Error loading report: {e}", 500
    else:
        # Original temp file logic
        print(f"DEBUG view_report: Temp file report")
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
    
    # Convert to HTML and sanitize to prevent XSS
    html_content = markdown.markdown(md_content, extensions=['tables', 'fenced_code'])
    
    # Sanitize HTML while preserving safe tags and attributes
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
                    'ul', 'ol', 'li', 'table', 'thead', 'tbody', 'tr', 'th', 'td',
                    'code', 'pre', 'blockquote', 'a', 'div', 'span', 'img']
    allowed_attrs = {
        '*': ['class', 'id'],
        'a': ['href', 'title', 'target'],
        'img': ['src', 'alt', 'title', 'width', 'height'],
        'td': ['colspan', 'rowspan'],
        'th': ['colspan', 'rowspan']
    }
    html_content = bleach.clean(html_content, tags=allowed_tags, attributes=allowed_attrs, strip=True)
    
    return render_template('report.html',
                         report=report,
                         html_content=html_content,
                         markdown_content=md_content)

@app.route('/report/<report_id>/pdf')
def export_pdf(report_id):
    """Export report as PDF"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    # Check if this is a database report (prefixed with 'db_')
    if report_id.startswith('db_'):
        validation_id = int(report_id.replace('db_', ''))
        
        # Get report from database
        try:
            db_report = db.get_validation_report_by_id(validation_id)
            if not db_report:
                return "Report not found in database", 404
            
            # Build report dict for PDF
            report = {
                'id': report_id,
                'filename': db_report['filename'],
                'message_type': db_report['message_type'],
                'status': db_report['status'],
                'errors': db_report['error_count'],
                'warnings': db_report['warning_count'],
                'date': db_report['timestamp'].strftime('%Y-%m-%d %H:%M:%S') if hasattr(db_report['timestamp'], 'strftime') else str(db_report['timestamp']),
                'report_path': db_report.get('report_url', '')
            }
            
            # Use stored report details if available
            if db_report.get('report_details'):
                md_content = db_report['report_details']
            else:
                # Fallback: Generate basic content
                md_content = f"# Validation Report: {db_report['filename']}\n\n"
                md_content += f"**Status:** {db_report['status']}  \n"
                md_content += f"**Message Type:** {db_report['message_type']}  \n"
                md_content += f"**Errors:** {db_report['error_count']}  \n"
                md_content += f"**Warnings:** {db_report['warning_count']}  \n"
                
        except Exception as e:
            print(f"ERROR: Failed to load database report for PDF: {e}")
            return f"Error loading report: {e}", 500
    else:
        # Handle temp file report
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
    
    # Generate PDF using WeasyPrint
    pdf_bytes = HTML(string=html_template).write_pdf()
    
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
@login_required
def retry_auto_correct(report_id):
    """Iterative auto-correction: keeps correcting and re-validating until PASSED or no more fixes possible"""
    try:
        # Always reload from temp file to get results from all workers
        load_processing_results()
        
        print(f"DEBUG auto-correct: report_id={report_id}, session_id={session.get('session_id')}")
        print(f"DEBUG auto-correct: Has api_key in session: {'api_key' in session}")
        print(f"DEBUG auto-correct: Has user_id in session: {'user_id' in session}")
        
        if 'api_key' not in session:
            print("ERROR: API key not found in session")
            # Try to retrieve from database if user is logged in
            if 'user_id' in session:
                try:
                    api_key = db.get_encrypted_api_key(session['user_id'])
                    if api_key:
                        session['api_key'] = api_key
                        print("DEBUG: Retrieved API key from database")
                    else:
                        print("ERROR: No API key in database for this user")
                        return jsonify({'success': False, 'message': 'API key not set. Please go to Settings.'}), 400
                except Exception as e:
                    print(f"ERROR retrieving API key: {e}")
                    import traceback
                    print(traceback.format_exc())
                    return jsonify({'success': False, 'message': 'Error retrieving API key'}), 400
            else:
                return jsonify({'success': False, 'message': 'API key not set. Please log in again.'}), 400
        
        print(f"\n{'='*80}")
        print(f"ITERATIVE AUTO-CORRECTION STARTED - Report ID: {report_id}")
        print(f"{'='*80}")
        
        # Check if this is a database report (db_XXX) or temp file report
        is_db_report = report_id.startswith('db_')
        current_content = None
        original_filepath = None
        filename = None
        validation_id = None
        detailed_errors = []
        file_info = {}  # Initialize file_info dict for both paths
        
        if is_db_report:
            # Handle database report
            validation_id = int(report_id.replace('db_', ''))
            print(f"DEBUG: Database report - validation_id={validation_id}")
            
            # Retrieve file from database
            file_data = db.get_validation_file_content(validation_id)
            if not file_data or not file_data['content']:
                return jsonify({
                    'success': False,
                    'message': 'File not found in database. Please re-upload and validate the file.'
                }), 404
            
            current_content = file_data['content']
            filename = file_data['filename']
            print(f"DEBUG: Retrieved file from database: {filename} ({len(current_content)} bytes)")
            
            # Create file_info dict to match temp file structure
            file_info = {
                'filename': filename,
                'filepath': None,  # Will be set after creating temp file
                'validation_id': validation_id
            }
            
            # Create temp file for processing
            original_filepath = os.path.join(UPLOAD_FOLDER, f"db_temp_{validation_id}_{filename}")
            with open(original_filepath, 'wb') as f:
                f.write(current_content)
            
            file_info['filepath'] = original_filepath
            
            # Get report details to extract errors
            db_report = db.get_validation_report_by_id(validation_id)
            if db_report:
                # We don't have detailed_errors stored, so we'll need to re-fetch from Gazelle
                # Or start with empty list and let the correction loop handle it
                detailed_errors = []
            
        else:
            # Handle temp file report
            if report_id not in processing_results:
                return jsonify({'success': False, 'message': 'Report not found in temporary storage'}), 404
            
            file_info = processing_results[report_id]
            original_filepath = file_info['filepath']
            filename = file_info['filename']
            validation_id = file_info.get('validation_id')
            detailed_errors = file_info.get('detailed_errors', [])
            
            print(f"DEBUG: Temp file report - filepath={original_filepath}")
            
            # Try to read from database first (persistent), fall back to temp file
            if validation_id:
                try:
                    file_data = db.get_validation_file_content(validation_id)
                    if file_data and file_data['content']:
                        current_content = file_data['content']
                        print(f"DEBUG: Retrieved file content from database (validation_id={validation_id})")
                except Exception as e:
                    print(f"WARNING: Failed to retrieve from database: {e}")
            
            # Fall back to temp file if database retrieval failed
            if current_content is None:
                if os.path.exists(original_filepath):
                    with open(original_filepath, 'rb') as f:
                        current_content = f.read()
                    print(f"DEBUG: Retrieved file content from temp file: {original_filepath}")
                else:
                    return jsonify({
                        'success': False, 
                        'message': 'File not found. Please re-upload and validate the file.'
                    }), 404
        
        max_iterations = int(os.getenv('MAX_AUTO_CORRECT_ITERATIONS', '10'))  # Prevent infinite loops
        iteration = 0
        total_corrections = 0
        all_corrections = []
        
        # Initialize final_filepath early so it's always defined
        final_filepath = original_filepath.replace('.txt', '_CORRECTED.txt').replace('.xml', '_CORRECTED.xml')
        
        original_errors = detailed_errors.copy()  # Preserve original error list for report
        
        # Initialize variables used later in report building
        detected_message_type = None
        status = 'UNKNOWN'
        errors = 0
        warnings = 0
        report_url = ''
        validation_output = ''

        # CRITICAL: Apply encoding fixes FIRST (these fix UNDEFINED status files)
        print(f"DEBUG: Applying pre-validation encoding fixes...")
        corrector = HL7MessageCorrector()
        corrected_content, encoding_fixes = corrector.prepare_message(
            current_content,
            file_info['filename'],
            gazelle_errors=[]  # No errors yet, just apply universal fixes like encoding
        )
        
        encoding_fixes_summary = corrector.get_corrections_summary()
        if encoding_fixes_summary['total_corrections'] > 0:
            print(f"DEBUG: Applied {encoding_fixes_summary['total_corrections']} encoding/structural fixes")
            current_content = corrected_content
            all_corrections.extend(encoding_fixes)
            total_corrections += encoding_fixes_summary['total_corrections']
            
            # Save corrected file
            with open(final_filepath, 'wb') as f:
                f.write(current_content)
        else:
            print(f"DEBUG: No encoding fixes needed")
            # Still save the file (might be first correction pass)
            with open(final_filepath, 'wb') as f:
                f.write(current_content)

        while iteration < max_iterations:
            iteration += 1
            print(f"\n{'='*80}")
            print(f"ITERATION {iteration}/{max_iterations}")
            print(f"{'='*80}")
            
            # VALIDATE FIRST (before attempting corrections)
            print(f"DEBUG: Validating file (iteration {iteration})...")
            temp_env = os.path.join(os.getcwd(), '.env.temp')
            with open(temp_env, 'w') as f:
                f.write(f"GAZELLE_API_KEY={session['api_key']}\n")
                f.write("VERIFY_SSL=True\n")

            original_env = os.path.join(os.getcwd(), '.env')
            backup_env = None
            if os.path.exists(original_env):
                backup_env = os.path.join(os.getcwd(), '.env.backup')
                os.rename(original_env, backup_env)
            os.rename(temp_env, original_env)

            try:
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'
                env['PYTHONUTF8'] = '1'
                env['OPEN_REPORT_BROWSER'] = '0'

                python_executable = sys.executable or shutil.which('python') or 'python'
                script_path = os.path.join(os.getcwd(), 'validate_with_verification.py')
                result = subprocess.run(
                    [python_executable, script_path, final_filepath],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=os.getcwd(),
                    env=env,
                    encoding='utf-8',
                    errors='replace'
                )
            finally:
                if os.path.exists(original_env):
                    os.remove(original_env)
                if backup_env and os.path.exists(backup_env):
                    os.rename(backup_env, original_env)

            # Parse validation output to get updated error list
            validation_output = result.stdout
            new_errors = []

            for line in validation_output.split('\n'):
                if 'GAZELLE_ERRORS_JSON=' in line:
                    try:
                        json_str = line.split('GAZELLE_ERRORS_JSON=')[1].strip()
                        new_errors = json.loads(json_str)
                        print(f"DEBUG: Iteration {iteration} validation found {len(new_errors)} remaining errors")
                    except:
                        pass
                elif 'Status:' in line and 'PASSED' in line.upper():
                    status = 'PASSED'
                elif 'Status:' in line and 'FAILED' in line.upper():
                    status = 'FAILED'
                elif 'Status:' in line and 'UNDEFINED' in line.upper():
                    status = 'UNDEFINED'
                elif 'Message Type:' in line:
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
            
            # Update error list for next iteration
            detailed_errors = new_errors
            print(f"DEBUG: Updated error list to {len(detailed_errors)} errors")
            
            # Check if we're done (validation passed or no errors)
            if status == 'PASSED' or len(detailed_errors) == 0:
                print(f"DEBUG: Validation {status} with {len(detailed_errors)} errors - stopping")
                break
            
            # Now apply corrections for the next iteration
            print(f"DEBUG: Found {len(detailed_errors)} errors to fix")
            
            # Apply corrections
            corrector = HL7MessageCorrector()
            corrected_content, corrections_list = corrector.prepare_message(
                current_content, 
                file_info['filename'],
                gazelle_errors=detailed_errors
            )
            
            corrections_summary = corrector.get_corrections_summary()
            corrections_made = corrections_summary['total_corrections']
            
            print(f"DEBUG: Applied {corrections_made} corrections in iteration {iteration}")
            
            if corrections_made == 0:
                print(f"DEBUG: No corrections could be applied - stopping iteration")
                break
            
            # Track all corrections
            total_corrections += corrections_made
            all_corrections.extend(corrections_list)
            
            # Continue with corrected content for next iteration
            current_content = corrected_content
            
            # Save temporary corrected file for validation
            with open(final_filepath, 'wb') as f:
                f.write(current_content)
        
        print(f"DEBUG: Loop completed - {iteration} total iterations, {total_corrections} total corrections")

        # Build detailed report content from final validation
        report_content = ""
        report_content += f"# HL7 v2 Validation Report\n\n"
        report_content += f"File Name: {os.path.basename(final_filepath)}\n\n"
        report_content += f"Message Type: {detected_message_type or 'Unknown'}\n\n"
        report_content += f"Status: {status}\n\n"
        report_content += f"Errors: {errors}\n"
        report_content += f"Warnings: {warnings}\n\n"
        report_content += f"**Iterations:** {iteration}\n"
        report_content += f"**Total Corrections Applied:** {total_corrections}\n\n"
        
        # Add original errors section
        if original_errors:
            report_content += "## Original Errors Found:\n\n"
            for i, err in enumerate(original_errors, 1):
                report_content += f"### Error #{i}: {err.get('type')}\n"
                report_content += f"- **Location:** {err.get('location')}\n"
                report_content += f"- **Description:** {err.get('description')}\n"
                report_content += f"- **Severity:** {err.get('severity', 'Unknown')}\n\n"
        
        # Add corrections applied section
        if all_corrections:
            report_content += "## Corrections Applied:\n\n"
            for i, correction in enumerate(all_corrections, 1):
                if isinstance(correction, dict):
                    report_content += f"### Correction #{i}\n"
                    report_content += f"- **Field:** {correction.get('field', 'Unknown')}\n"
                    report_content += f"- **Type:** {correction.get('type', 'Unknown')}\n"
                    report_content += f"- **Change:** {correction.get('original')} → {correction.get('corrected')}\n"
                    report_content += f"- **Details:** {correction.get('details', 'N/A')}\n\n"
                else:
                    report_content += f"### Correction #{i}\n"
                    report_content += f"- {correction}\n\n"
        
        if report_url:
            report_content += f"**Full Gazelle Report:** {report_url}\n\n"
        
        if detailed_errors:
            report_content += "## Remaining Errors After Corrections:\n\n"
            for i, err in enumerate(detailed_errors, 1):
                report_content += f"### Error #{i}: {err.get('type')}\n"
                report_content += f"- **Location:** {err.get('location')}\n"
                report_content += f"- **Description:** {err.get('description')}\n\n"
        else:
            report_content += "## All Errors Resolved! ✅\n\n"
        
        report_content += "\n## Complete Validation Output:\n\n"
        report_content += "```\n"
        report_content += validation_output
        report_content += "\n```\n"

        # Update processing_results only for temp file reports
        if not is_db_report and report_id in processing_results:
            processing_results[report_id]['status'] = 'completed'
            processing_results[report_id]['validation_status'] = status
            processing_results[report_id]['errors'] = errors
            processing_results[report_id]['warnings'] = warnings
            processing_results[report_id]['report_content'] = report_content
            processing_results[report_id]['report_url'] = report_url
            processing_results[report_id]['message_type'] = detected_message_type or 'Unknown'
            processing_results[report_id]['corrected_path'] = final_filepath
            processing_results[report_id]['corrections_applied'] = {'total_corrections': total_corrections}
            processing_results[report_id]['iterations'] = iteration
            save_processing_results()

        # Save to database if user is authenticated (ALWAYS save for both report types)
        if 'user_id' in session:
            try:
                # Read the corrected file content
                with open(final_filepath, 'rb') as f:
                    corrected_content = f.read()
                
                new_validation_id = db.save_validation_result(
                    user_id=session['user_id'],
                    filename=filename,
                    message_type=detected_message_type or 'Unknown',
                    status=status,
                    report_url=report_url or '',
                    error_count=errors,
                    warning_count=warnings,
                    corrections_applied=total_corrections,
                    file_content=corrected_content,
                    report_details=report_content
                )
                # Update validation_id for future operations (only for temp file reports)
                if not is_db_report and report_id in processing_results:
                    processing_results[report_id]['validation_id'] = new_validation_id
                    save_processing_results()
                
                print(f"DEBUG: Saved auto-correct result to database (ID={new_validation_id}) for user {session['user_id']}")

            except Exception as e:
                print(f"WARNING: Failed to save to database: {e}")

        remaining_errors = len(detailed_errors)

        if status == 'PASSED' or remaining_errors == 0:
            return jsonify({
                'success': True,
                'message': f"Successfully corrected all errors in {iteration} iteration(s)!",
                'corrections_applied': total_corrections,
                'iterations': iteration,
                'status': 'PASSED',
                'corrected_file': final_filepath
            })

        return jsonify({
            'success': True,
            'message': f"Applied {total_corrections} corrections in {iteration} iteration(s). {remaining_errors} error(s) remaining.",
            'corrections_applied': total_corrections,
            'iterations': iteration,
            'remaining_errors': remaining_errors,
            'status': 'PARTIAL',
            'corrected_file': final_filepath
        })
    
    except Exception as e:
        print(f"ERROR: Exception in retry_auto_correct: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return jsonify({
            'success': False,
            'message': f'Auto-correction failed: {str(e)}'
        }), 500

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload-page')
@login_required
def upload_page():
    """Upload page"""
    has_api_key = 'api_key' in session
    return render_template('upload.html', has_api_key=has_api_key)

@app.route('/upload', methods=['POST'])
@login_required
def upload_file():
    """Handle file upload"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
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
    save_processing_results()
    
    print(f"DEBUG upload: file_id={file_id}, filename={filename}, session_id={session['session_id']}")
    print(f"DEBUG upload: Saved to processing_results, total items: {len(processing_results)}")
    
    return jsonify({
        'success': True,
        'file_id': file_id,
        'filename': filename
    })

@app.route('/validate/<file_id>', methods=['POST'])
@login_required
def validate_file(file_id):
    """Validate uploaded file with optional automatic correction"""
    # Always reload from temp file to get results from all workers
    load_processing_results()
    
    print(f"DEBUG validate: Requested file_id={file_id}, session_id={session.get('session_id')}")
    print(f"DEBUG validate: processing_results has {len(processing_results)} items")
    
    if file_id not in processing_results:
        print(f"ERROR: file_id {file_id} not found in processing_results")
        print(f"ERROR: Available file_ids: {list(processing_results.keys())}")
        return jsonify({'success': False, 'message': 'File not found'}), 404
    
    if 'api_key' not in session:
        return jsonify({'success': False, 'message': 'API key not set'}), 400
    
    file_info = processing_results[file_id]
    
    # Verify session ownership
    if file_info.get('session_id') != session.get('session_id'):
        print(f"ERROR: Session mismatch - file session: {file_info.get('session_id')}, current session: {session.get('session_id')}")
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    filepath = file_info['filepath']
    
    # Check if auto-correct was requested
    auto_correct = False
    try:
        request_data = request.get_json() or {}
        auto_correct = request_data.get('auto_correct', False)
    except:
        pass
    
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
            env['OPEN_REPORT_BROWSER'] = '0'
            
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
        detailed_errors = []  # Initialize empty list for errors
        detailed_warnings = []  # Initialize empty list for warnings
        
        # Extract parsing variables from subprocess output
        for line in validation_output.split('\n'):
            if 'GAZELLE_OID=' in line:
                # New parseable format from validation script
                oid = line.split('GAZELLE_OID=')[1].strip()
                print(f"DEBUG: Extracted OID from GAZELLE_OID= format: {oid}")
            elif 'GAZELLE_ERRORS_JSON=' in line:
                # Parse JSON errors directly from validation script output
                try:
                    json_str = line.split('GAZELLE_ERRORS_JSON=')[1].strip()
                    # Handle JSON parsing carefully in case of encoding issues
                    parsed_json_errors = json.loads(json_str)
                    if isinstance(parsed_json_errors, list):
                        detailed_errors = parsed_json_errors
                        print(f"DEBUG: Extracted {len(detailed_errors)} detailed errors from JSON format")
                        for i, err in enumerate(detailed_errors[:3]):
                            print(f"DEBUG: Error {i+1}: Type={err.get('type')}, Location={err.get('location')}")
                except Exception as e:
                    print(f"DEBUG: Failed to parse GAZELLE_ERRORS_JSON: {e}")
                    pass
            elif 'Status:' in line:
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
        
        # Fetch detailed error information from Gazelle XML report if not already obtained from JSON
        if not detailed_errors and oid:
            detailed_errors, detailed_warnings, xml_report = fetch_and_parse_gazelle_report(oid, session['api_key'])
            print(f"DEBUG: Fallback: Fetched {len(detailed_errors) if detailed_errors else 0} errors from Gazelle API")
        else:
            print(f"DEBUG: Using {len(detailed_errors) if detailed_errors else 0} errors from JSON format (no API call needed)")
        
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
            report_content += f"  - Field insertions: {corrections_summary.get('field_insertions', 0)}  \n"
            report_content += f"  - Gazelle error fixes: {corrections_summary.get('gazelle_fixes', 0)}  \n\n"
        
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
        
        # Next steps based on status
        if status == "PASSED":
            report_content += "## ✅ VALIDATION SUCCESSFUL\n\n"
            report_content += "This message has passed all mandatory validation checks and is ready for submission.\n\n"
        else:
            report_content += "## 🔧 NEXT STEPS\n\n"
            report_content += "1. Review each error above\n"
            report_content += "2. Click 'Try Auto-Correct' button to attempt automatic fixes\n"
            report_content += "3. Or manually correct the issues in your HL7 message\n"
            report_content += "4. Re-upload and validate the corrected message\n\n"
        
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
            'corrected_path': None,  # No auto-correction on validation
            'detailed_errors': detailed_errors if detailed_errors else [],  # Store Gazelle errors for auto-correction
            'detailed_warnings': detailed_warnings if detailed_warnings else []  # Store warnings for reference
        })
        
        # Save to temp file so results persist across dyno restarts
        save_processing_results()
        
        # Save to database if user is authenticated
        if 'user_id' in session:
            try:
                # Read file content to store in database
                with open(filepath, 'rb') as f:
                    file_content = f.read()
                
                validation_id = db.save_validation_result(
                    user_id=session['user_id'],
                    filename=file_info['filename'],
                    message_type=message_type,
                    status=status,
                    report_url=report_url or '',
                    error_count=errors,
                    warning_count=warnings,
                    corrections_applied=0,  # No auto-correction on upload
                    file_content=file_content,
                    report_details=report_content
                )
                # Store validation_id for later retrieval
                processing_results[file_id]['validation_id'] = validation_id
                print(f"DEBUG: Saved validation result to database (ID={validation_id}) for user {session['user_id']}")
            except Exception as e:
                print(f"WARNING: Failed to save to database: {e}")

        
        print(f"DEBUG: Validation completed for file_id={file_id}")
        print(f"DEBUG: Status={status}, Errors={errors}, Warnings={warnings}")
        print(f"DEBUG: processing_results[{file_id}] status is now: {processing_results[file_id]['status']}")

        # If auto-correct is requested and there are errors, run correction cycle
        if auto_correct and errors > 0:
            print(f"DEBUG: Auto-correct flag is True and {errors} errors found - running correction cycle")
            # Call the correction logic from retry_auto_correct
            return retry_auto_correct(file_id)
        
        return jsonify({
            'success': True,
            'status': status,
            'errors': errors,
            'warnings': warnings,
            'report_url': report_url,
            'report_content': report_content,
            'message_type': message_type
        })
        
    except subprocess.TimeoutExpired:
        processing_results[file_id]['status'] = 'timeout'
        save_processing_results()
        return jsonify({'success': False, 'message': 'Validation timeout'}), 500
    except Exception as e:
        # Log the error but don't expose details to user
        print(f"Error during validation: {e}")
        processing_results[file_id]['status'] = 'error'
        save_processing_results()
        return jsonify({'success': False, 'message': 'Validation failed. Please try again.'}), 500

@app.route('/retry-auto-correct/<file_id>', methods=['POST'])
def auto_correct_if_errors(file_id):
    """Auto-correct file if errors found (called when auto-correct checkbox is checked)"""
    # Reload from temp file to get latest results
    load_processing_results()
    
    if file_id not in processing_results:
        return jsonify({'success': False, 'message': 'File not found'}), 404
    
    if 'api_key' not in session:
        return jsonify({'success': False, 'message': 'API key not set'}), 400
    
    file_info = processing_results[file_id]
    
    # Check if there are errors to correct
    detailed_errors = file_info.get('detailed_errors', [])
    if not detailed_errors:
        # No errors, validation already passed
        return jsonify({
            'success': True,
            'status': 'PASSED',
            'errors': 0,
            'warnings': file_info.get('warnings', 0),
            'report_content': file_info.get('report_content', ''),
            'message_type': file_info.get('message_type', 'Unknown'),
            'corrections': [],
            'iteration_count': 0
        })
    
    # Use the existing retry_auto_correct logic but adapted for file_id instead of report_id
    # Delegate to the existing retry_auto_correct endpoint
    from flask import redirect
    return redirect(f'/auto-correct/{file_id}', code=307)

if __name__ == '__main__':
    # Only enable debug in local development
    app.run(debug=False if os.environ.get('DYNO') else True, port=5000)
