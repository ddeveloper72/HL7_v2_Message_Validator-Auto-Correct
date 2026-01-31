"""
Comprehensive HL7 v2 Message Correction Module
Integrates all discovered fixes for Gazelle EVS validation
Uses data-driven approach with HL7 standard code tables.
"""
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from hl7_code_tables import is_valid_code, get_valid_codes, find_similar_code


class HL7MessageCorrector:
    """Auto-correct HL7 v2 XML messages for Gazelle EVS validation"""
    
    def __init__(self):
        self.corrections_made = []
        self.attempts = 0
        self.max_attempts = 3
        
    def prepare_message(self, xml_content, filename="message.xml", gazelle_errors=None):
        """
        Prepare HL7 message for validation by applying all necessary corrections.
        
        Args:
            xml_content: Raw XML content (bytes or string)
            filename: Original filename for tracking
            gazelle_errors: List of detailed error dicts from Gazelle validation (optional)
            
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
        
        # Step 5: Apply Gazelle error-driven corrections (NEW)
        if gazelle_errors:
            content = self._apply_gazelle_error_fixes(content, gazelle_errors)
        
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
        """Apply code corrections using data-driven HL7 code tables"""
        
        # Known problematic codes with their locations and table associations
        # These are discovered through validation but validated against HL7 standards
        corrections = [
            {
                'invalid_value': 'MCN.HLPracticeID',
                'pattern': '<HD.3>MCN.HLPracticeID</HD.3>',
                'table': 'HL70301',  # Universal ID Type
                'location': 'MSH-6.3 / MSH-4.3',
                'field': 'Universal ID Type (HD.3)',
                'reason': 'MCN.HLPracticeID is not a valid HL70301 code'
            },
            {
                'invalid_value': 'HIPEHOS',
                'pattern': '<EI.4>HIPEHOS</EI.4>',
                'table': 'HL70301',  # Universal ID Type
                'location': 'SCH-2.4',
                'field': 'Universal ID Type (EI.4)',
                'reason': 'HIPEHOS is not a valid HL70301 code'
            },
            {
                'invalid_value': 'XXX',
                'pattern': '>XXX<',
                'table': 'HL70070',  # Specimen Source Code
                'location': 'OBR-15.1',
                'field': 'Specimen Source Code (CE.1)',
                'reason': 'XXX is not a valid HL70070 specimen source code'
            }
        ]
        
        for correction in corrections:
            invalid_value = correction['invalid_value']
            pattern = correction['pattern']
            table = correction['table']
            
            if pattern in content:
                # Find a valid replacement code from HL7 standards
                replacement = find_similar_code(table, invalid_value)
                
                if replacement:
                    content = content.replace(pattern, pattern.replace(invalid_value, replacement))
                    self.corrections_made.append({
                        'type': 'CODE_FIX',
                        'field': correction['field'],
                        'location': correction['location'],
                        'old_value': invalid_value,
                        'new_value': replacement,
                        'table': table,
                        'description': f'Invalid code corrected from {invalid_value} to {replacement}',
                        'reason': correction['reason'],
                        'source': 'HL7 Code Tables'
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
    
    def _apply_gazelle_error_fixes(self, content, gazelle_errors):
        """
        Apply targeted fixes based on Gazelle validation errors.
        
        Args:
            content: XML content string
            gazelle_errors: List of error dicts from Gazelle with keys:
                - type: Error type (e.g., 'Cardinality', 'Code', 'Datatype')
                - location: HL7 path (e.g., 'hl7shortpath:SCH[1]-20[1]')
                - description: Error description
                - priority: 'MANDATORY', 'REQUIRED', 'OPTIONAL'
                - severity: 'ERROR', 'WARNING'
        
        Returns:
            str: Content with targeted fixes applied
        """
        if not gazelle_errors:
            print("DEBUG: No Gazelle errors provided to _apply_gazelle_error_fixes")
            return content
        
        print(f"DEBUG: Processing {len(gazelle_errors)} Gazelle errors")
        
        for i, error in enumerate(gazelle_errors):
            error_type = error.get('type', '')
            location = error.get('location', '')
            description = error.get('description', '')
            priority = error.get('priority', '')
            severity = error.get('severity', '')
            
            print(f"DEBUG: Error {i+1}: type={error_type}, severity={severity}, location={location}")
            print(f"DEBUG: Description: {description[:100]}")
            
            # Skip warnings - process errors and items with empty severity (treat as errors)
            # Empty severity usually means it's an error from the Gazelle report
            if severity and severity.upper() == 'WARNING':
                print(f"DEBUG: Skipping - is a WARNING")
                continue
            
            print(f"DEBUG: Processing this error (severity={severity or 'empty/assumed ERROR'})")
            
            # Fix 1: Missing required fields (Cardinality errors)
            if error_type == 'Cardinality' and 'missing' in description.lower():
                content = self._fix_missing_field(content, location, description)
            
            # Fix 2: Invalid code values (Code errors or Code Not Found errors)
            elif ('Code' in error_type or 'code' in error_type.lower()) and 'not member of' in description.lower():
                content = self._fix_invalid_code(content, location, description)
            
            # Fix 3: Empty required components
            elif 'required' in description.lower() and 'missing' in description.lower():
                content = self._fix_missing_component(content, location, description)
        
        return content
    
    def _fix_missing_field(self, content, location, description):
        """Fix missing required HL7 fields"""
        # Parse location like 'hl7shortpath:SCH[1]-20[1]' -> SCH-20
        match = re.search(r':([A-Z]{3})\[1\]-(\d+)', location)
        if not match:
            return content
        
        segment = match.group(1)
        field_num = match.group(2)
        
        # Check if this is a known fixable field
        if segment == 'SCH' and field_num == '20':
            # SCH-20: Entered By Person - can add empty XCN structure
            pattern = rf'(<{segment}\.{field_num}>)(\s*)(</\w+\.\d+>)'
            if re.search(pattern, content):
                # Field exists but is empty - fill with minimal structure
                def add_empty_xcn(match):
                    self.corrections_made.append({
                        'type': 'GAZELLE_FIX',
                        'field': f'{segment}-{field_num} (Entered By Person)',
                        'location': location,
                        'value': 'SYSTEM^AUTO^CORRECTOR',
                        'description': f'Added placeholder for missing required field {segment}-{field_num}',
                        'reason': description,
                        'source': 'Gazelle Error Report'
                    })
                    return f'{match.group(1)}SYSTEM^AUTO^CORRECTOR{match.group(3)}'
                
                content = re.sub(pattern, add_empty_xcn, content)
        
        return content
    
    def _fix_invalid_code(self, content, location, description):
        """Fix invalid code values and code systems reported by Gazelle"""
        print(f"DEBUG: _fix_invalid_code called")
        print(f"DEBUG:   location={location}")
        print(f"DEBUG:   description={description[:150]}")
        
        # Extract the invalid value from description
        # Example: "The value 'HIPEHOS' at location ... is not member of the value set [HL70301]"
        # Or: "The code 'OTH' and code system 'L' at location Component OBR-15.1"
        # Or: "The value 'CLIP' at location ... is not member of the value set [HL70301_HL]"
        value_match = re.search(r"(?:value|code) '([^']+)'", description)
        # Extract table number - matches HL70301, HL70070, etc. within brackets
        table_match = re.search(r'\[(HL7\d+)(?:_[A-Z]+)?\]', description)
        codesystem_match = re.search(r"code system '([^']+)'", description)
        
        if not value_match:
            print(f"DEBUG:   Could not extract invalid value from description using regex")
            return content
        
        invalid_value = value_match.group(1)
        invalid_codesystem = codesystem_match.group(1) if codesystem_match else None
        # Extract full table name directly (e.g., 'HL70070')
        full_table = table_match.group(1) if table_match else 'Unknown'
        
        print(f"DEBUG:   Found invalid value: '{invalid_value}'")
        print(f"DEBUG:   Invalid code system: {invalid_codesystem}")
        print(f"DEBUG:   Table: {full_table}")
        
        # Check if the code itself is valid but the code system is wrong
        is_code_valid = is_valid_code(full_table, invalid_value)
        
        if is_code_valid and invalid_codesystem and invalid_codesystem != full_table:
            # The code is correct, but the code system field is wrong
            print(f"DEBUG:   Code '{invalid_value}' is VALID in {full_table}, but code system '{invalid_codesystem}' is WRONG")
            print(f"DEBUG:   Need to fix code system field from '{invalid_codesystem}' to '{full_table}' or empty")
            
            # Find and replace the code system field (usually CE.3)
            # Pattern: <CE.1>OTH</CE.1>...<CE.3>L</CE.3>
            # Replace CE.3 value with correct code system or empty
            codesys_pattern = f'(<CE\\.3>){re.escape(invalid_codesystem)}(</CE\\.3>)'
            if re.search(codesys_pattern, content):
                print(f"DEBUG:   Found CE.3 with value '{invalid_codesystem}', replacing with empty")
                old_len = len(content)
                # Replace with empty or the correct code system
                # For HL7 standard, often CE.3 should be empty when using standard tables
                content = re.sub(codesys_pattern, r'\1\2', content)  # Empty value
                new_len = len(content)
                print(f"DEBUG:   Replacement complete. Content size: {old_len} -> {new_len} bytes")
                
                self.corrections_made.append({
                    'type': 'GAZELLE_FIX',
                    'field': f'Code system at {location}',
                    'location': location,
                    'old_value': invalid_codesystem,
                    'new_value': '(empty)',
                    'code': invalid_value,
                    'table': full_table,
                    'description': f'Corrected invalid code system from {invalid_codesystem} to empty',
                    'reason': description,
                    'source': 'HL7 Code Tables (Data-Driven)'
                })
                return content
            else:
                print(f"DEBUG:   Could not find CE.3 pattern with '{invalid_codesystem}'")
        
        # If code is not valid, find replacement
        if not is_code_valid:
            # Use data-driven approach to find valid replacement
            print(f"DEBUG:   Looking up replacement for invalid code '{invalid_value}' in {full_table}")
            correct_value = find_similar_code(full_table, invalid_value)
            
            if correct_value:
                print(f"DEBUG:   Data-driven lookup found: '{invalid_value}' -> '{correct_value}' in {full_table}")
                
                # Different replacement strategies based on location
                replaced = False
                
                # Strategy 1: Simple pattern replacement for HD.3, EI.4, etc
                search_pattern = f'>{invalid_value}<'
                if search_pattern in content:
                    print(f"DEBUG:   Found pattern '{search_pattern}' in content, replacing with '>{correct_value}<'")
                    old_len = len(content)
                    content = content.replace(search_pattern, f'>{correct_value}<')
                    new_len = len(content)
                    replaced = True
                    print(f"DEBUG:   Replacement complete. Content size: {old_len} -> {new_len} bytes")
                
                # Strategy 2: For CE.1 fields
                if not replaced:
                    ce_patterns = [
                        (f'<CE\\.1>{re.escape(invalid_value)}</CE\\.1>', f'<CE.1>{correct_value}</CE.1>'),
                        (f'<SPS\\.1><CE\\.1>{re.escape(invalid_value)}</CE\\.1>', f'<SPS.1><CE.1>{correct_value}</CE.1>'),
                        (f'>{re.escape(invalid_value)}<', f'>{correct_value}<'),
                    ]
                    
                    for pattern, replacement in ce_patterns:
                        if re.search(pattern, content):
                            print(f"DEBUG:   Found CE pattern, replacing...")
                            old_len = len(content)
                            content = re.sub(pattern, replacement, content)
                            new_len = len(content)
                            replaced = True
                            print(f"DEBUG:   Replacement complete. Content size: {old_len} -> {new_len} bytes")
                            break
                
                if replaced:
                    self.corrections_made.append({
                        'type': 'GAZELLE_FIX',
                        'field': f'Code value at {location}',
                        'location': location,
                        'old_value': invalid_value,
                        'old_codesystem': invalid_codesystem,
                        'new_value': correct_value,
                        'table': full_table,
                        'description': f'Corrected invalid code value based on Gazelle error',
                        'reason': description,
                        'source': 'HL7 Code Tables (Data-Driven)'
                    })
                else:
                    print(f"DEBUG:   Could not find where to replace '{invalid_value}' in content")
            else:
                print(f"DEBUG:   Data-driven lookup FAILED - no valid replacement found for '{invalid_value}' in {full_table}")
                print(f"DEBUG:   This code may need manual intervention or addition to hl7_code_tables.json")
        
        return content
    
    def _fix_missing_component(self, content, location, description):
        """Fix missing required components within fields"""
        # Parse location to identify segment and field
        # Example: 'hl7shortpath:SCH[1]-6[1].3[1]' -> SCH-6.3
        match = re.search(r':([A-Z]{3})\[1\]-(\d+)\[1\]\.(\d+)', location)
        if not match:
            return content
        
        segment = match.group(1)
        field_num = match.group(2)
        component = match.group(3)
        
        # Known fixes for missing components
        if segment == 'SCH' and field_num == '6' and component == '3':
            # SCH-6.3: Name of coding system for appointment reason
            pattern = rf'(<{segment}\.{field_num}>.*?<CE\.{component}>)(\s*)(</CE\.{component}>)'
            
            def add_coding_system(match):
                if match.group(2).strip() == '':
                    self.corrections_made.append({
                        'type': 'GAZELLE_FIX',
                        'field': f'{segment}-{field_num}.{component} (Name of coding system)',
                        'location': location,
                        'value': 'HL70276',
                        'description': f'Added missing coding system for appointment reason',
                        'reason': description,
                        'source': 'Gazelle Error Report'
                    })
                    return f'{match.group(1)}HL70276{match.group(3)}'
                return match.group(0)
            
            content = re.sub(pattern, add_coding_system, content, flags=re.DOTALL)
        
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
        gazelle_fixes = [c for c in self.corrections_made if c['type'] == 'GAZELLE_FIX']
        
        if critical:
            report.append(f"\n## Critical Fixes ({len(critical)})\n")
            for i, corr in enumerate(critical, 1):
                report.append(f"### {i}. {corr['description']}")
                report.append(f"**Reason:** {corr['reason']}\n")
        
        if gazelle_fixes:
            report.append(f"\n## Gazelle Error-Driven Fixes ({len(gazelle_fixes)})\n")
            for i, corr in enumerate(gazelle_fixes, 1):
                report.append(f"### {i}. {corr['description']}")
                report.append(f"- **Location:** {corr['location']}")
                if 'old_value' in corr:
                    report.append(f"- **Old Value:** `{corr['old_value']}`")
                    report.append(f"- **New Value:** `{corr['new_value']}`")
                elif 'value' in corr:
                    report.append(f"- **Value Added:** `{corr['value']}`")
                report.append(f"- **Gazelle Error:** {corr['reason']}\n")
        
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
            'gazelle_fixes': len([c for c in self.corrections_made if c['type'] == 'GAZELLE_FIX']),
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
