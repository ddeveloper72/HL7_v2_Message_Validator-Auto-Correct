"""
Auto-correct module for HL7 v2 messages
Provides the auto_correct_and_validate function used by dashboard_app
"""
import os
from hl7_corrector import HL7MessageCorrector
import base64
import requests
from pathlib import Path


def auto_correct_and_validate(filepath, detailed_errors, api_key):
    """
    Attempt to auto-correct an HL7 message and validate it
    
    Args:
        filepath: Path to the HL7 XML file
        detailed_errors: List of validation errors from previous validation
        api_key: Gazelle API key for validation
        
    Returns:
        dict: {
            'success': bool,
            'corrected_file': str (path to corrected file if successful),
            'correction_report': str (markdown formatted report),
            'error': str (error message if failed)
        }
    """
    try:
        # Read the original file
        with open(filepath, 'rb') as f:
            original_content = f.read()
        
        # Apply corrections using HL7MessageCorrector
        corrector = HL7MessageCorrector()
        corrected_bytes, corrections_list = corrector.prepare_message(original_content, os.path.basename(filepath))
        
        # Generate correction report
        correction_report = _generate_correction_report(corrections_list)
        
        # Save corrected file
        corrected_filepath = filepath.replace('.xml', '_corrected.xml').replace('.txt', '_corrected.txt')
        with open(corrected_filepath, 'wb') as f:
            f.write(corrected_bytes)
        
        return {
            'success': True,
            'corrected_file': corrected_filepath,
            'correction_report': correction_report
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def _generate_correction_report(corrections_list):
    """
    Generate a markdown-formatted report of corrections made
    
    Args:
        corrections_list: List of correction dictionaries from HL7MessageCorrector
        
    Returns:
        str: Markdown formatted report
    """
    if not corrections_list:
        return "No corrections needed.\n"
    
    report = ""
    for i, correction in enumerate(corrections_list, 1):
        report += f"\n#### Correction {i}\n"
        report += f"- **Type:** {correction.get('type', 'Unknown')}\n"
        report += f"- **Description:** {correction.get('description', 'No description')}\n"
        
        if 'field' in correction:
            report += f"- **Field:** {correction['field']}\n"
        if 'location' in correction:
            report += f"- **Location:** {correction['location']}\n"
        if 'old_value' in correction:
            report += f"- **Old Value:** `{correction['old_value']}`\n"
        if 'new_value' in correction:
            report += f"- **New Value:** `{correction['new_value']}`\n"
        if 'reason' in correction:
            report += f"- **Reason:** {correction['reason']}\n"
        if 'critical' in correction and correction['critical']:
            report += f"- **Critical:** ⚠️ Yes\n"
    
    return report
