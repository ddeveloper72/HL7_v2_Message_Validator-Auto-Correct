"""
HL7 Validation Workflow with Verification
Only confirms corrections after receiving DONE_PASSED from validator
"""
import os
import base64
import requests
import json
import time
import webbrowser
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
                # Still processing
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
        
        # Define namespaces
        ns = {'gvr': 'http://validationreport.gazelle.ihe.net/'}
        
        # Get overall result
        validation_overview = root.find('.//gvr:validationOverview', ns)
        if validation_overview is not None:
            overall_result = validation_overview.get('validationOverallResult', 'UNKNOWN')
        else:
            overall_result = root.get('result', 'UNKNOWN')
        
        # Get counters
        counters = root.find('.//gvr:counters', ns)
        error_count = 0
        warning_count = 0
        
        if counters is not None:
            error_count = int(counters.get('numberOfErrors', 0))
            warning_count = int(counters.get('numberOfWarnings', 0))
        
        # Get mandatory errors and warnings
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

def validate_file_with_verification(file_path, show_warnings=False):
    """Complete validation workflow with verification"""
    print(f"\n{'='*80}")
    print(f"VALIDATING: {os.path.basename(file_path)}")
    print(f"{'='*80}")
    
    # Step 1: Submit validation
    print("\n📤 Step 1: Submitting to Gazelle EVS...")
    result, error = submit_validation(file_path)
    
    if error:
        print(f"❌ Submission failed: {error}")
        return False
    
    print(f"✅ Submitted successfully")
    print(f"   OID: {result['oid']}")
    print(f"   Message Type: {result['message_type']}")
    
    # Step 2: Wait for validation to complete
    print(f"\n⏳ Step 2: Waiting for validation to complete...")
    xml_report, error = check_validation_status(result['oid'])
    
    if error:
        print(f"❌ Failed to get validation report: {error}")
        return False
    
    print(f"✅ Validation completed")
    
    # Step 3: Parse results
    print(f"\n🔍 Step 3: Checking validation results...")
    parsed_result, error = parse_validation_result(xml_report)
    
    if error:
        print(f"❌ Failed to parse results: {error}")
        return False
    
    # Step 4: Report results
    print(f"\n{'='*80}")
    print(f"VALIDATION RESULTS")
    print(f"{'='*80}")
    print(f"Status: {parsed_result['status']}")
    print(f"Errors: {parsed_result['error_count']} (MANDATORY: {len(parsed_result['mandatory_errors'])})")
    print(f"Warnings: {parsed_result['warning_count']}")
    
    # Build report URL
    report_url = f"{BASE_URL}/evs/report.seam?oid={result['oid']}&privacyKey={result['privacy_key']}"
    print(f"\n🔗 Report: {report_url}")
    
    if parsed_result['status'] == 'PASSED':
        print(f"\n✅ ✅ ✅ VALIDATION PASSED! ✅ ✅ ✅")
        print(f"\n🎉 File is CONFIRMED CORRECT by validator!")
        
        # Check if there are warnings and if user wants to see them
        if parsed_result['warnings'] and show_warnings:
            print(f"\n{'='*80}")
            print(f"OPTIONAL: WARNINGS TO ADDRESS ({len(parsed_result['warnings'])} total)")
            print(f"{'='*80}")
            print(f"\n⚠️  These warnings don't prevent PASSED status, but you may want to address them:")
            
            for i, warning in enumerate(parsed_result['warnings'], 1):
                print(f"\n  Warning #{i}:")
                print(f"    Location: {warning['location']}")
                print(f"    Type: {warning['type']}")
                print(f"    Issue: {warning['description']}")
            
            print(f"\n💡 Note: File already passes validation. Fixing warnings is optional.")
        elif parsed_result['warnings'] and not show_warnings:
            print(f"\n💡 TIP: Use --warnings flag to see {parsed_result['warning_count']} optional warnings")
        
        webbrowser.open(report_url)
        return True
    
    else:
        print(f"\n❌ VALIDATION FAILED")
        
        if parsed_result['mandatory_errors']:
            print(f"\n📋 MANDATORY ERRORS TO FIX:")
            for i, error in enumerate(parsed_result['mandatory_errors'], 1):
                print(f"\n  Error #{i}:")
                print(f"    Location: {error['location']}")
                print(f"    Issue: {error['description']}")
        
        print(f"\n⚠️  File is NOT yet correct - additional fixes needed")
        webbrowser.open(report_url)
        return False

def main():
    """Test validation with verification"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python validate_with_verification.py <file_path> [--warnings]")
        print("\nArguments:")
        print("  <file_path>    Path to HL7 file to validate")
        print("  --warnings     Optional: Show and document warnings (in addition to errors)")
        print("\nExamples:")
        print("  python validate_with_verification.py 'Healthlink Tests/SIU_S12_CORRECTED.txt'")
        print("  python validate_with_verification.py 'Healthlink Tests/ORU_R01.txt' --warnings")
        return
    
    file_path = sys.argv[1]
    show_warnings = '--warnings' in sys.argv or '-w' in sys.argv
    
    if not os.path.exists(file_path):
        print(f"❌ File not found: {file_path}")
        return
    
    is_valid = validate_file_with_verification(file_path, show_warnings)
    
    if is_valid:
        print(f"\n✅ SUCCESS: File passed validation!")
        sys.exit(0)
    else:
        print(f"\n❌ FAILED: File needs more corrections")
        sys.exit(1)

if __name__ == "__main__":
    main()
