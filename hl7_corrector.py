"""
Comprehensive HL7 v2 Message Correction Module
Integrates all discovered fixes for Gazelle EVS validation
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime


class HL7MessageCorrector:
    """Auto-correct HL7 v2 XML messages for Gazelle EVS validation"""
    
    def __init__(self):
        self.corrections_made = []
        self.attempts = 0
        self.max_attempts = 3
        
    def prepare_message(self, xml_content, filename="message.xml"):
        """
        Prepare HL7 message for validation by applying all necessary corrections.
        
        Args:
            xml_content: Raw XML content (bytes or string)
            filename: Original filename for tracking
            
        Returns:
            tuple: (corrected_content_bytes, corrections_list)
        """
        self.corrections_made = []
        self.attempts = 0
        
        # Convert to string if bytes
        if isinstance(xml_content, bytes):
            # Try to decode, handling BOM
            try:
                content = xml_content.decode('utf-8-sig')
            except:
                content = xml_content.decode('utf-8', errors='ignore')
        else:
            content = xml_content
        
        # Step 1: Remove BOM if present (CRITICAL FIX)
        content = self._remove_bom(content)
        
        # Step 2: Ensure XML declaration
        content = self._ensure_xml_declaration(content)
        
        # Step 3: Apply code corrections
        content = self._apply_code_corrections(content)
        
        # Step 4: Fix empty required fields
        content = self._fix_empty_required_fields(content)
        
        # Convert back to bytes for validation
        corrected_bytes = content.encode('utf-8')
        
        return corrected_bytes, self.corrections_made
    
    def _remove_bom(self, content):
        """Remove UTF-8 BOM that breaks Gazelle XML→ER7 conversion"""
        # Remove BOM character from string
        if content.startswith('\ufeff'):
            content = content[1:]
            self.corrections_made.append({
                'type': 'BOM_REMOVAL',
                'description': 'Removed UTF-8 BOM (Byte Order Mark)',
                'reason': 'BOM prevents Gazelle XML→ER7 converter from parsing',
                'critical': True
            })
        return content
    
    def _ensure_xml_declaration(self, content):
        """Ensure proper XML declaration at start"""
        if not content.strip().startswith('<?xml'):
            content = '<?xml version="1.0" encoding="utf-8"?>\n' + content
            self.corrections_made.append({
                'type': 'XML_DECLARATION',
                'description': 'Added XML declaration header',
                'reason': 'Required for proper XML parsing',
                'critical': True
            })
        return content
    
    def _apply_code_corrections(self, content):
        """Apply all known code value corrections"""
        
        # Fix 1: MCN.HLPracticeID → L (MSH-6.3, MSH-4.3, PID-3.4.3)
        if 'MCN.HLPracticeID' in content:
            content = content.replace(
                '<HD.3>MCN.HLPracticeID</HD.3>',
                '<HD.3>L</HD.3>'
            )
            self.corrections_made.append({
                'type': 'CODE_FIX',
                'field': 'Universal ID Type (HD.3)',
                'location': 'MSH-6.3 / MSH-4.3',
                'old_value': 'MCN.HLPracticeID',
                'new_value': 'L',
                'table': 'HL70301',
                'description': 'Invalid Universal ID Type code corrected to Local (L)',
                'reason': 'MCN.HLPracticeID is not a valid HL7 v2.2 Table 0301 code'
            })
        
        # Fix 2: HIPEHOS → L (SCH-2.4 for SIU messages)
        if 'HIPEHOS' in content:
            content = content.replace(
                '<EI.4>HIPEHOS</EI.4>',
                '<EI.4>L</EI.4>'
            )
            self.corrections_made.append({
                'type': 'CODE_FIX',
                'field': 'Universal ID Type (EI.4)',
                'location': 'SCH-2.4',
                'old_value': 'HIPEHOS',
                'new_value': 'L',
                'table': 'HL70301',
                'description': 'HIPE Hospital System code corrected to Local (L)',
                'reason': 'HIPEHOS is not a valid HL7 v2.2 Table 0301 code'
            })
        
        return content
    
    def _fix_empty_required_fields(self, content):
        """Fix empty required fields in HL7 messages"""
        
        # Fix empty SCH-6.3 (name of coding system) in SIU messages
        if '<SIU_S12' in content or '<SIU_S13' in content:
            # Pattern: Find empty CE.3 within SCH.6
            pattern = r'(<SCH\.6>.*?<CE\.3>)(\s*)(</CE\.3>)'
            
            def replace_empty_sch6_ce3(match):
                if match.group(2).strip() == '':  # Only if truly empty
                    self.corrections_made.append({
                        'type': 'FIELD_INSERTION',
                        'field': 'Name of Coding System (CE.3)',
                        'location': 'SCH-6.3',
                        'value': 'HL70276',
                        'description': 'Filled empty required field with appointment reason code system',
                        'reason': 'SCH-6.3 is required when SCH-6 is present'
                    })
                    return f"{match.group(1)}HL70276{match.group(3)}"
                return match.group(0)
            
            content = re.sub(pattern, replace_empty_sch6_ce3, content, flags=re.DOTALL)
        
        return content
    
    def get_correction_report(self):
        """Generate human-readable correction report"""
        if not self.corrections_made:
            return "No corrections were needed."
        
        report = []
        report.append(f"# HL7 Message Auto-Correction Report")
        report.append(f"\n**Total Corrections Applied:** {len(self.corrections_made)}\n")
        
        # Group by type
        critical = [c for c in self.corrections_made if c.get('critical')]
        code_fixes = [c for c in self.corrections_made if c['type'] == 'CODE_FIX']
        field_insertions = [c for c in self.corrections_made if c['type'] == 'FIELD_INSERTION']
        
        if critical:
            report.append(f"\n## Critical Fixes ({len(critical)})\n")
            for i, corr in enumerate(critical, 1):
                report.append(f"### {i}. {corr['description']}")
                report.append(f"**Reason:** {corr['reason']}\n")
        
        if code_fixes:
            report.append(f"\n## Code Value Corrections ({len(code_fixes)})\n")
            for i, corr in enumerate(code_fixes, 1):
                report.append(f"### {i}. {corr['field']} at {corr['location']}")
                report.append(f"- **Table:** {corr['table']}")
                report.append(f"- **Old Value:** `{corr['old_value']}`")
                report.append(f"- **New Value:** `{corr['new_value']}`")
                report.append(f"- **Reason:** {corr['reason']}\n")
        
        if field_insertions:
            report.append(f"\n## Field Insertions ({len(field_insertions)})\n")
            for i, corr in enumerate(field_insertions, 1):
                report.append(f"### {i}. {corr['field']} at {corr['location']}")
                report.append(f"- **Value Inserted:** `{corr['value']}`")
                report.append(f"- **Reason:** {corr['reason']}\n")
        
        return "\n".join(report)
    
    def get_corrections_summary(self):
        """Get simple summary for API response"""
        return {
            'total_corrections': len(self.corrections_made),
            'critical_fixes': len([c for c in self.corrections_made if c.get('critical')]),
            'code_fixes': len([c for c in self.corrections_made if c['type'] == 'CODE_FIX']),
            'field_insertions': len([c for c in self.corrections_made if c['type'] == 'FIELD_INSERTION']),
            'corrections': self.corrections_made
        }


# Convenience function for single-use
def auto_correct_hl7_message(xml_content, filename="message.xml"):
    """
    Auto-correct HL7 v2 XML message.
    
    Returns:
        tuple: (corrected_bytes, corrections_dict)
    """
    corrector = HL7MessageCorrector()
    corrected_bytes, corrections = corrector.prepare_message(xml_content, filename)
    summary = corrector.get_corrections_summary()
    return corrected_bytes, summary
