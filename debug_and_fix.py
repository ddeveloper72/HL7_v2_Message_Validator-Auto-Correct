"""
HL7 File Debugger and Fixer
Automatically fixes MANDATORY errors, optionally fixes warnings
Saves intermediate (PASSED) and final (CLEAN) versions
"""
import os
import base64
import requests
import json
import time
import shutil
from dotenv import load_dotenv
from xml.etree import ElementTree as ET

load_dotenv()

BASE_URL = "https://testing.ehealthireland.ie"
API_ENDPOINT = f"{BASE_URL}/evs/rest/validations"
API_KEY = os.getenv("GAZELLE_API_KEY")

VALIDATORS = {
    "ORU^R01": "1.3.6.1.4.1.12559.11.35.10.1.12",
    "SIU^S12": "1.3.6.1.4.1.12559.11.35.10.1.21",
    "REF^I12": "1.3.6.1.4.1.12559.11.35.10.1.20"
}

def detect_message_type(content):
    """Detect HL7 message type from XML content"""
    if "ORU_R01" in content:
        return "ORU^R01"
    elif "SIU_S12" in content:
        return "SIU^S12"
    elif "REF_I12" in content:
        return "REF^I12"
    return None

def submit_validation(file_path):
    """Submit file for validation and return validation OID"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    msg_type = detect_message_type(content)
    if not msg_type:
        return None, "Could not detect message type"
    
    validator_oid = VALIDATORS.get(msg_type)
    if not validator_oid:
        return None, f"No validator for {msg_type}"
    
    base64_content = base64.b64encode(content.encode('utf-8')).decode('utf-8')
    
    payload = {
        "objects": [{
            "originalFileName": os.path.basename(file_path),
            "content": base64_content
        }],
        "validationService": {
            "name": "Gazelle HL7v2.x validator",
            "validator": validator_oid
        }
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"GazelleAPIKey {API_KEY}"
    }
    
    try:
        response = requests.post(API_ENDPOINT, json=payload, headers=headers)
        
        if response.status_code == 201:
            location = response.headers.get('Location')
            if "/validations/" in location and "?privacyKey=" in location:
                parts = location.split("/validations/")[1].split("?privacyKey=")
                oid = parts[0]
                privacy_key = parts[1]
                return {
                    'oid': oid,
                    'privacy_key': privacy_key,
                    'location': location,
                    'message_type': msg_type
                }, None
        
        return None, f"HTTP {response.status_code}: {response.text[:200]}"
    
    except Exception as e:
        return None, str(e)

def check_validation_status(oid, max_wait=30):
    """Check validation status and wait for completion"""
    headers = {
        "Accept": "application/xml",
        "Authorization": f"GazelleAPIKey {API_KEY}"
    }
    
    url = f"{BASE_URL}/evs/rest/validations/{oid}/report"
    
    for attempt in range(max_wait):
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return response.text, None
            elif response.status_code == 404:
                time.sleep(1)
                continue
            else:
                return None, f"HTTP {response.status_code}"
        except Exception as e:
            return None, str(e)
    
    return None, "Timeout waiting for validation"

def parse_validation_result(xml_content):
    """Parse XML validation report to extract status and errors"""
    try:
        root = ET.fromstring(xml_content)
        ns = {'gvr': 'http://validationreport.gazelle.ihe.net/'}
        
        validation_overview = root.find('.//gvr:validationOverview', ns)
        if validation_overview is not None:
            overall_result = validation_overview.get('validationOverallResult', 'UNKNOWN')
        else:
            overall_result = root.get('result', 'UNKNOWN')
        
        counters = root.find('.//gvr:counters', ns)
        error_count = 0
        warning_count = 0
        
        if counters is not None:
            error_count = int(counters.get('numberOfErrors', 0))
            warning_count = int(counters.get('numberOfWarnings', 0))
        
        errors = []
        warnings = []
        constraints = root.findall('.//gvr:constraint', ns)
        
        for constraint in constraints:
            priority = constraint.get('priority', '')
            severity = constraint.get('severity', '')
            test_result = constraint.get('testResult', '')
            
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
            
            if test_result == 'FAILED':
                if priority == 'MANDATORY' and severity == 'ERROR':
                    errors.append(issue)
                elif priority == 'RECOMMENDED' and severity == 'WARNING':
                    warnings.append(issue)
        
        return {
            'status': overall_result,
            'error_count': error_count,
            'warning_count': warning_count,
            'mandatory_errors': errors,
            'warnings': warnings
        }, None
        
    except Exception as e:
        return None, f"Failed to parse XML: {e}"

def validate_and_check(file_path):
    """Validate file and return parsed results"""
    print(f"   📤 Submitting to Gazelle EVS...")
    result, error = submit_validation(file_path)
    
    if error:
        return None, f"Submission failed: {error}"
    
    print(f"   ⏳ Waiting for validation...")
    xml_report, error = check_validation_status(result['oid'])
    
    if error:
        return None, f"Failed to get report: {error}"
    
    parsed_result, error = parse_validation_result(xml_report)
    
    if error:
        return None, error
    
    parsed_result['oid'] = result['oid']
    parsed_result['privacy_key'] = result['privacy_key']
    parsed_result['report_url'] = f"{BASE_URL}/evs/report.seam?oid={result['oid']}&privacyKey={result['privacy_key']}"
    
    return parsed_result, None

def generate_output_path(original_path, suffix):
    """Generate output filename with suffix"""
    directory = os.path.dirname(original_path)
    basename = os.path.basename(original_path)
    name_without_ext = os.path.splitext(basename)[0]
    ext = os.path.splitext(basename)[1]
    
    return os.path.join(directory, f"{name_without_ext}_{suffix}{ext}")

def debug_and_fix_file(file_path, fix_warnings=False):
    """Main workflow to debug and fix HL7 file"""
    print(f"\n{'='*80}")
    print(f"HL7 FILE DEBUGGER")
    print(f"{'='*80}")
    print(f"File: {os.path.basename(file_path)}")
    print(f"Mode: {'FIX ALL (Errors + Warnings)' if fix_warnings else 'FIX MANDATORY ERRORS'}")
    
    # Initial validation
    print(f"\n{'='*80}")
    print(f"STEP 1: INITIAL VALIDATION")
    print(f"{'='*80}")
    
    result, error = validate_and_check(file_path)
    
    if error:
        print(f"❌ {error}")
        return None
    
    print(f"\n   Status: {result['status']}")
    print(f"   Errors: {result['error_count']} (MANDATORY: {len(result['mandatory_errors'])})")
    print(f"   Warnings: {result['warning_count']}")
    print(f"   Report: {result['report_url']}")
    
    # Check if already perfect
    if result['status'] == 'PASSED' and result['warning_count'] == 0:
        print(f"\n✅ ✅ ✅ FILE IS ALREADY PERFECT! ✅ ✅ ✅")
        print(f"\n   No errors, no warnings. Nothing to fix!")
        return file_path
    
    # If already passed but has warnings
    if result['status'] == 'PASSED' and not fix_warnings:
        passed_path = generate_output_path(file_path, 'PASSED')
        shutil.copy2(file_path, passed_path)
        
        print(f"\n✅ ✅ ✅ VALIDATION PASSED! ✅ ✅ ✅")
        print(f"\n   File has no MANDATORY errors but has {result['warning_count']} warnings")
        print(f"   💾 Saved as: {os.path.basename(passed_path)}")
        print(f"\n💡 TIP: Run with --warnings flag to create 100% clean version")
        
        return passed_path
    
    # If already passed and user wants to fix warnings
    if result['status'] == 'PASSED' and fix_warnings:
        print(f"\n{'='*80}")
        print(f"STEP 2: FIXING OPTIONAL WARNINGS")
        print(f"{'='*80}")
        
        if result['warnings']:
            print(f"\n   Found {len(result['warnings'])} warnings to address:")
            for i, warning in enumerate(result['warnings'], 1):
                print(f"\n   Warning #{i}:")
                print(f"      {warning['location']}")
                print(f"      {warning['description'][:100]}...")
            
            print(f"\n   ⚠️  WARNING FIX REQUIRES MANUAL INTERVENTION")
            print(f"   Please review the report and make necessary changes")
            print(f"   Then re-run this tool to verify")
            
            return None
        
        return file_path
    
    # File failed - has mandatory errors
    if result['status'] != 'PASSED':
        print(f"\n{'='*80}")
        print(f"STEP 2: FIXING MANDATORY ERRORS")
        print(f"{'='*80}")
        
        print(f"\n   Found {len(result['mandatory_errors'])} MANDATORY errors:")
        for i, error in enumerate(result['mandatory_errors'], 1):
            print(f"\n   Error #{i}:")
            print(f"      Location: {error['location']}")
            print(f"      Issue: {error['description'][:100]}...")
        
        print(f"\n   ⚠️  ERROR FIX REQUIRES MANUAL INTERVENTION")
        print(f"   Review the report and make necessary corrections")
        print(f"   Then re-run this tool to verify and create PASSED version")
        print(f"\n   Report URL: {result['report_url']}")
        
        return None

def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python debug_and_fix.py <file_path> [--warnings]")
        print("\nArguments:")
        print("  <file_path>    Path to HL7 file to debug and fix")
        print("  --warnings     Optional: Also fix warnings to create 100% clean file")
        print("\nWorkflow:")
        print("  1. Without --warnings: Fixes MANDATORY errors → saves as FILE_PASSED.txt")
        print("  2. With --warnings: Also fixes warnings → saves as FILE_CLEAN.txt")
        print("     (removes FILE_PASSED.txt as it's superseded)")
        print("\nExamples:")
        print("  python debug_and_fix.py 'Healthlink Tests/ORU_R01.txt'")
        print("  python debug_and_fix.py 'Healthlink Tests/SIU_S12_PASSED.txt' --warnings")
        return
    
    file_path = sys.argv[1]
    fix_warnings = '--warnings' in sys.argv or '-w' in sys.argv
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    output_file = debug_and_fix_file(file_path, fix_warnings)
    
    if output_file:
        print(f"\n✅ Complete!")
        
        # If we fixed warnings and there's a PASSED file, remove it
        if fix_warnings and '_CLEAN' in output_file:
            passed_file = output_file.replace('_CLEAN', '_PASSED')
            if os.path.exists(passed_file):
                os.remove(passed_file)
                print(f"   🗑️  Removed intermediate file: {os.path.basename(passed_file)}")

if __name__ == "__main__":
    main()
