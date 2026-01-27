"""
Enhanced HL7 Validator with Automatic XML Report Parsing
Fetches validation reports in XML format and automatically analyzes errors
"""
import requests
import base64
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

EVS_BASE_URL = 'https://testing.ehealthireland.ie'
EVS_VALIDATION_ENDPOINT = f'{EVS_BASE_URL}/evs/rest/validations'
GAZELLE_API_KEY = os.getenv('GAZELLE_API_KEY', '')

VALIDATORS = {
    'ORU^R01': {
        'oid': '1.3.6.1.4.1.12559.11.35.10.1.12',
        'name': 'Laboratory Results (HL-12)'
    },
    'SIU^S12': {
        'oid': '1.3.6.1.4.1.12559.11.35.10.1.21',
        'name': 'Appointment Notification (HL-8)'
    },
    'REF^I12': {
        'oid': '1.3.6.1.4.1.12559.11.35.10.1.20',
        'name': 'Discharge Summary (HL-3)'
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

def submit_validation(file_path):
    """Submit file for validation and return location"""
    print(f"\n{'='*80}")
    print(f"📄 FILE: {os.path.basename(file_path)}")
    print(f"{'='*80}")
    
    with open(file_path, 'rb') as f:
        xml_content = f.read()
    
    msg_type = detect_message_type(xml_content)
    if not msg_type:
        print("❌ ERROR: Could not detect message type")
        return None
    
    validator_info = VALIDATORS[msg_type]
    print(f"📋 Message Type: {msg_type}")
    print(f"🔍 Validator: {validator_info['name']}")
    
    base64_content = base64.b64encode(xml_content).decode('utf-8')
    
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
            verify=True
        )
        
        if response.status_code == 201:
            location = response.headers.get('Location', '')
            print("✅ Validation submitted successfully!")
            
            return {
                'file': file_path,
                'message_type': msg_type,
                'validator': validator_info,
                'location': location,
                'status': 'submitted'
            }
        else:
            print(f"❌ Validation failed: HTTP {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return None

def fetch_xml_report(location):
    """Fetch validation report in XML format"""
    print(f"\n⏳ Fetching XML validation report...")
    
    # Extract OID and privacy key from location
    oid_with_key = location.split('validations/')[-1]
    oid_parts = oid_with_key.split('?')
    oid = oid_parts[0]
    privacy_key = oid_parts[1].split('=')[-1] if len(oid_parts) > 1 else ''
    
    # Try different URL formats for XML report
    report_urls = [
        f"{location}/report",  # REST API format
        f"{EVS_BASE_URL}/evs/report.seam?oid={oid}&privacyKey={privacy_key}",  # Web UI format
    ]
    
    for url in report_urls:
        try:
            print(f"   Trying: {url}")
            response = requests.get(
                url,
                headers={
                    'Accept': 'application/xml',
                    'Authorization': f'GazelleAPIKey {GAZELLE_API_KEY}'
                },
                timeout=30,
                verify=True
            )
            
            if response.status_code == 200:
                print(f"   ✅ Got XML report ({len(response.text)} bytes)")
                return response.text
            else:
                print(f"   ❌ HTTP {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    return None

def parse_validation_xml(xml_content):
    """Parse XML validation report and extract errors/warnings"""
    try:
        root = ET.fromstring(xml_content)
        
        results = {
            'errors': [],
            'warnings': [],
            'passed': 0,
            'total': 0,
            'status': 'unknown'
        }
        
        # Try to find validation results in XML
        # This depends on the actual XML structure returned by Gazelle
        # We may need to adjust this based on the actual response
        
        # Look for common XML patterns
        for elem in root.iter():
            tag = elem.tag.lower()
            
            if 'error' in tag:
                results['errors'].append({
                    'tag': elem.tag,
                    'text': elem.text,
                    'attribs': elem.attrib
                })
            elif 'warning' in tag:
                results['warnings'].append({
                    'tag': elem.tag,
                    'text': elem.text,
                    'attribs': elem.attrib
                })
            elif 'constraint' in tag:
                # Parse constraint violations
                constraint_data = {
                    'tag': elem.tag,
                    'attribs': elem.attrib
                }
                for child in elem:
                    constraint_data[child.tag] = child.text
                
                if elem.attrib.get('priority', '').upper() == 'MANDATORY':
                    results['errors'].append(constraint_data)
                else:
                    results['warnings'].append(constraint_data)
        
        return results
        
    except Exception as e:
        print(f"   ⚠️ Could not parse XML: {str(e)}")
        return None

def display_validation_results(result, xml_report):
    """Display validation results in readable format"""
    print(f"\n{'='*80}")
    print(f"📊 VALIDATION RESULTS: {os.path.basename(result['file'])}")
    print(f"{'='*80}")
    
    if xml_report:
        # Try to parse the report
        parsed = parse_validation_xml(xml_report)
        
        if parsed:
            print(f"\n✅ Passed: {parsed['passed']}")
            print(f"⚠️ Warnings: {len(parsed['warnings'])}")
            print(f"❌ Errors: {len(parsed['errors'])}")
            
            if parsed['errors']:
                print(f"\n{'='*80}")
                print("ERRORS FOUND:")
                print(f"{'='*80}")
                for i, error in enumerate(parsed['errors'], 1):
                    print(f"\n{i}. {error.get('tag', 'Unknown')}")
                    for key, value in error.items():
                        if key not in ['tag', 'attribs'] and value:
                            print(f"   {key}: {value}")
        else:
            print("\n📄 Raw XML Report:")
            print(xml_report[:2000])  # Show first 2000 chars
            
    else:
        print("\n⚠️ Could not fetch XML report")
    
    # Save raw XML
    xml_file = f"validation_report_{os.path.basename(result['file']).replace('.txt', '')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
    if xml_report:
        with open(xml_file, 'w', encoding='utf-8') as f:
            f.write(xml_report)
        print(f"\n💾 Raw XML saved: {xml_file}")

def main():
    """Main workflow"""
    print("\n" + "="*80)
    print("🔬 HL7 VALIDATOR WITH AUTOMATIC XML REPORT ANALYSIS")
    print("="*80)
    
    test_files = [
        r'Healthlink Tests\ORU_R01.txt',
        r'Healthlink Tests\SIU_S12.txt',
        r'Healthlink Tests\SIU_S12_CORRECTED.txt'
    ]
    
    for file_path in test_files:
        if not os.path.exists(file_path):
            print(f"\n❌ File not found: {file_path}")
            continue
        
        # Submit validation
        result = submit_validation(file_path)
        
        if result and result.get('location'):
            # Fetch XML report
            xml_report = fetch_xml_report(result['location'])
            
            # Display results
            display_validation_results(result, xml_report)

if __name__ == '__main__':
    main()
