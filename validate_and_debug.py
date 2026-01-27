"""
Enhanced HL7 Message Debugger with Web Report Viewing
Automatically validates, displays errors, and provides debugging guidance
"""
import requests
import base64
import json
import os
import webbrowser
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

EVS_BASE_URL = 'https://testing.ehealthireland.ie'
EVS_VALIDATION_ENDPOINT = f'{EVS_BASE_URL}/evs/rest/validations'
GAZELLE_API_KEY = os.getenv('GAZELLE_API_KEY', '')
VERIFY_SSL = True

VALIDATORS = {
    'ORU^R01': {
        'oid': '1.3.6.1.4.1.12559.11.35.10.1.12',
        'name': 'Laboratory Results (HL-12)',
        'transaction': 'HL-12'
    },
    'SIU^S12': {
        'oid': '1.3.6.1.4.1.12559.11.35.10.1.21',
        'name': 'Appointment Notification (HL-8)',
        'transaction': 'HL-8'
    },
    'REF^I12': {
        'oid': '1.3.6.1.4.1.12559.11.35.10.1.20',
        'name': 'Discharge Summary (HL-3)',
        'transaction': 'HL-3'
    }
}

def detect_message_type(xml_content):
    """Detect HL7 message type from XML content"""
    content_str = xml_content.decode('utf-8') if isinstance(xml_content, bytes) else xml_content
    
    if '<ORU_R01' in content_str:
        return 'ORU^R01'
    elif '<SIU_S12' in content_str:
        return 'SIU^S12'
    elif '<REF_I12' in content_str:
        return 'REF^I12'
    
    return None

def validate_and_get_report(file_path):
    """Validate message and return web report URL"""
    print(f"\n{'='*80}")
    print(f"📄 FILE: {os.path.basename(file_path)}")
    print(f"{'='*80}")
    
    # Read file
    with open(file_path, 'rb') as f:
        xml_content = f.read()
    
    # Detect message type
    msg_type = detect_message_type(xml_content)
    if not msg_type:
        print("❌ ERROR: Could not detect message type")
        return None
    
    validator_info = VALIDATORS[msg_type]
    print(f"📋 Message Type: {msg_type}")
    print(f"🔍 Validator: {validator_info['name']}")
    print(f"🆔 OID: {validator_info['oid']}")
    
    # Encode in base64
    base64_content = base64.b64encode(xml_content).decode('utf-8')
    
    # Prepare payload
    payload = {
        "objects": [{
            "originalFileName": os.path.basename(file_path),
            "content": base64_content
        }],
        "validationService": {
            "name": "Gazelle HL7v2.x validator",
            "validator": validator_info['oid']
        }
    }
    
    # Submit validation
    print("\n⏳ Submitting to Gazelle EVS...")
    try:
        response = requests.post(
            EVS_VALIDATION_ENDPOINT,
            json=payload,
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'GazelleAPIKey {GAZELLE_API_KEY}'
            },
            timeout=30,
            verify=VERIFY_SSL
        )
        
        if response.status_code == 201:
            location = response.headers.get('Location', '')
            print("✅ Validation submitted successfully!")
            print(f"\n📍 Validation ID: {location.split('/')[-1]}")
            
            # Convert REST API URL to permanent report URL
            # REST: /evs/rest/validations/OID?privacyKey=KEY
            # Permanent Report: /evs/report.seam?oid=OID&privacyKey=KEY
            if location:
                oid_with_key = location.split('validations/')[-1]
                oid_parts = oid_with_key.split('?')
                oid = oid_parts[0]
                privacy_key = oid_parts[1].split('=')[-1] if len(oid_parts) > 1 else ''
                
                web_url = f"{EVS_BASE_URL}/evs/report.seam?oid={oid}&privacyKey={privacy_key}"
                
                return {
                    'file': file_path,
                    'message_type': msg_type,
                    'validator': validator_info,
                    'status': 'success',
                    'oid': oid,
                    'privacy_key': privacy_key,
                    'rest_url': location,
                    'web_url': web_url
                }
        else:
            print(f"❌ Validation failed: HTTP {response.status_code}")
            print(f"Response: {response.text[:300]}")
            return {
                'file': file_path,
                'message_type': msg_type,
                'status': 'failed',
                'error': response.text,
                'status_code': response.status_code
            }
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {
            'file': file_path,
            'message_type': msg_type,
            'status': 'error',
            'error': str(e)
        }

def main():
    """Main workflow"""
    print("\n" + "="*80)
    print("🔬 HL7 MESSAGE VALIDATOR AND DEBUGGER")
    print("Testing HealthLink Messages Against Gazelle EVS")
    print("="*80)
    
    test_files = [
        r'Healthlink Tests\ORU_R01.txt',
        r'Healthlink Tests\SIU_S12.txt'
    ]
    
    results = []
    
    # Validate each file
    for file_path in test_files:
        if os.path.exists(file_path):
            result = validate_and_get_report(file_path)
            if result:
                results.append(result)
        else:
            print(f"\n❌ File not found: {file_path}")
    
    # Display results and open reports
    if results:
        print("\n" + "="*80)
        print("📊 VALIDATION RESULTS")
        print("="*80)
        
        for i, result in enumerate(results, 1):
            print(f"\n{i}. {os.path.basename(result['file'])}")
            print(f"   Type: {result['message_type']}")
            print(f"   Status: {result['status'].upper()}")
            
            if result['status'] == 'success':
                print(f"   ✅ View Report: {result['web_url']}")
                print(f"\n   Opening validation report in browser...")
                webbrowser.open(result['web_url'])
            elif result['status'] == 'failed':
                print(f"   ❌ Error: {result.get('error', 'Unknown error')[:200]}")
        
        # Save summary
        summary_file = f"validation_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Summary saved: {summary_file}")
        
        print("\n" + "="*80)
        print("📝 NEXT STEPS")
        print("="*80)
        print("\n1. Review validation reports in your browser")
        print("2. Note any errors or warnings")
        print("3. I will help you fix the errors and create corrected versions")
        print("4. Re-test the corrected files to verify they pass")
        print("\n" + "="*80)
        
        # Wait for user input
        input("\nPress Enter after reviewing the validation reports...")
        
        # Now analyze errors
        print("\n" + "="*80)
        print("🔍 ERROR ANALYSIS")
        print("="*80)
        print("\nPlease describe any errors you see in the validation reports,")
        print("or paste the error messages here, and I'll help fix them.")
        
    else:
        print("\n❌ No results to display")

if __name__ == '__main__':
    main()
