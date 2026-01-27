"""
HL7 Message Error Analysis and Auto-Correction Tool
Based on Gazelle EVS validation results
"""

# ============================================================================
# SIU_S12.txt - VALIDATION ERRORS (DONE_FAILED)
# ============================================================================

ERRORS_SIU_S12 = [
    {
        'error_id': 1,
        'description': "The value 'HIPEHOS' at location Component SCH-2.4 (universal ID type) is not member of the value set [HL70301]",
        'location': 'hl7/shortpath:SCH[1]-2[1].4',
        'priority': 'MANDATORY',
        'constraint_type': 'Code Not Found',
        'plain_language': """
        ERROR: Invalid Universal ID Type
        
        What went wrong:
        - In the SCH-2 field (Placer Appointment ID), component 4 contains "HIPEHOS"
        - This should be a valid Universal ID Type from HL7 table 0301
        - "HIPEHOS" is not a valid code in this table
        
        Valid values from HL70301 include:
        - DNS = Domain Name System
        - GUID = Globally Unique Identifier  
        - HCD = CEN Healthcare Coding Identifier
        - HL7 = HL7 registration schemes
        - ISO = ISO Object Identifier
        - L = Local
        - M = Medical record number
        - N = National person identifier
        - U = Unspecified
        - UUID = Universal Unique Identifier
        - x400 = X.400 MHS identifier
        - x500 = X.500 directory name
        
        How to fix:
        - Change SCH-2.4 from "HIPEHOS" to a valid code
        - Most likely should be "L" (Local) or "ISO"
        - Or remove this component if not needed
        """,
        'fix': 'Change <EI.4>HIPEHOS</EI.4> to <EI.4>L</EI.4> or remove it'
    },
    {
        'error_id': 2,
        'description': "The required Field SCH-20 (Entered By Person) is missing",
        'location': 'hl7/shortpath:SCH[1]-20[1]',
        'priority': 'MANDATORY',
        'constraint_type': 'Usage',
        'plain_language': """
        ERROR: Missing Required Field
        
        What went wrong:
        - The SCH segment requires field SCH-20 (Entered By Person)
        - This field is MANDATORY but is missing from the message
        
        What this field means:
        - SCH-20 identifies the person who entered/created the appointment
        - It should contain provider/staff information (ID, name, etc.)
        
        How to fix:
        - Add SCH-20 field to the SCH segment
        - Use XCN (Extended Composite ID Number and Name) format
        - Include at least ID number and/or name
        
        Example structure:
        <SCH.20>
          <XCN.1>12345</XCN.1>
          <XCN.2>
            <FN.1>SMITH</FN.1>
          </XCN.2>
          <XCN.3>JOHN</XCN.3>
        </SCH.20>
        """,
        'fix': 'Add <SCH.20> field with staff/provider who entered the appointment'
    }
]

# ============================================================================
# ORU_R01.txt - VALIDATION ERRORS (DONE_FAILED)
# ============================================================================

ERRORS_ORU_R01 = [
    # Based on screenshot showing DONE_FAILED status
    # Need to see detailed report for specific errors
    {
        'note': 'Validation failed - need to view detailed report to see specific errors'
    }
]

# ============================================================================
# CORRECTED FILE: SIU_S12.txt
# ============================================================================

CORRECTED_SIU_S12 = """<SIU_S12 xmlns="urn:hl7-org:v2xml">
  <MSH>
    <MSH.1>|</MSH.1>
    <MSH.2>^~\\&amp;</MSH.2>
    <MSH.3>
      <HD.1>TOREX.HEALTHLINK.8</HD.1>
      <HD.2></HD.2>
      <HD.3></HD.3>
    </MSH.3>
    <MSH.4>
      <HD.1>AMNCH</HD.1>
      <HD.2>1049</HD.2>
      <HD.3>L</HD.3>
    </MSH.4>
    <MSH.6>
      <HD.1>DR LIAM STRONG</HD.1>
      <HD.2>09999</HD.2>
      <HD.3>L</HD.3>
    </MSH.6>
    <MSH.7>
      <TS.1>201301260352</TS.1>
    </MSH.7>
    <MSH.9>
      <MSG.1>SIU</MSG.1>
      <MSG.2>S12</MSG.2>
    </MSH.9>
    <MSH.10>3988215</MSH.10>
    <MSH.11>
      <PT.1>P</PT.1>
    </MSH.11>
    <MSH.12>
      <VID.1>2.4</VID.1>
    </MSH.12>
  </MSH>
  <SCH>
    <SCH.2>
      <EI.1>74043860</EI.1>
      <EI.2>AMNCH</EI.2>
      <EI.3>1049</EI.3>
      <EI.4>L</EI.4>
    </SCH.2>
    <SCH.6>
      <CE.1>D.N.A.</CE.1>
      <CE.2>D.N.A.</CE.2>
      <CE.3></CE.3>
    </SCH.6>
    <SCH.7>
      <CE.1></CE.1>
      <CE.2></CE.2>
      <CE.3></CE.3>
    </SCH.7>
    <SCH.11>
      <TQ.4>
        <TS.1>201301250850</TS.1>
      </TQ.4>
      <TQ.6></TQ.6>
    </SCH.11>
    <SCH.16>
      <XCN.1></XCN.1>
      <XCN.2>
        <FN.1 />
      </XCN.2>
      <XCN.3></XCN.3>
      <XCN.4></XCN.4>
      <XCN.5></XCN.5>
      <XCN.6></XCN.6>
    </SCH.16>
    <SCH.20>
      <XCN.1>ADMIN001</XCN.1>
      <XCN.2>
        <FN.1>ADMIN</FN.1>
      </XCN.2>
      <XCN.3>STAFF</XCN.3>
      <XCN.4></XCN.4>
      <XCN.5></XCN.5>
      <XCN.6></XCN.6>
    </SCH.20>
    <SCH.25>
      <CE.1>Cancelled</CE.1>
      <CE.2>The indicated appointment was stopped from occurring (cancelled prior to starting)</CE.2>
      <CE.3>HL70278</CE.3>
    </SCH.25>
  </SCH>
  <NTE>
    <NTE.1 />
    <NTE.2 />
    <NTE.3 />
  </NTE>
  <SIU_S12.PATIENT>
    <PID>
      <PID.3>
        <CX.1>1234567</CX.1>
        <CX.2></CX.2>
        <CX.3></CX.3>
        <CX.4>
          <HD.1>AMNCH</HD.1>
          <HD.2 />
          <HD.3 />
        </CX.4>
        <CX.5>MRN</CX.5>
      </PID.3>
      <PID.5>
        <XPN.1>
          <FN.1>BLOGGS</FN.1>
        </XPN.1>
        <XPN.2>JOE</XPN.2>
        <XPN.3></XPN.3>
        <XPN.4></XPN.4>
        <XPN.5>MR</XPN.5>
        <XPN.6></XPN.6>
        <XPN.7>L</XPN.7>
      </PID.5>
      <PID.7>
        <TS.1>19590521</TS.1>
      </PID.7>
      <PID.8>M</PID.8>
      <PID.11>
        <XAD.1>
          <SAD.1>MAIN ROAD</SAD.1>
        </XAD.1>
        <XAD.2>MAINTOWN</XAD.2>
        <XAD.3>DUBLIN 7</XAD.3>
        <XAD.4 />
        <XAD.5 />
      </PID.11>
      <PID.13>
        <XTN.1 />
        <XTN.4 />
        <XTN.6 />
        <XTN.7 />
      </PID.13>
      <PID.29>
        <TS.1 />
      </PID.29>
      <PID.30>N</PID.30>
    </PID>
    <PV1>
      <PV1.2>O</PV1.2>
      <PV1.3>
        <PL.1></PL.1>
        <PL.2></PL.2>
        <PL.3></PL.3>
        <PL.4>
          <HD.1></HD.1>
          <HD.2 />
          <HD.3 />
        </PL.4>
        <PL.5></PL.5>
        <PL.6></PL.6>
        <PL.7></PL.7>
        <PL.8></PL.8>
        <PL.9>MR P. O BRIEN GLAUCOMA CLINIC</PL.9>
      </PV1.3>
      <PV1.7>
        <XCN.1 />
        <XCN.2>
          <FN.1 />
        </XCN.2>
        <XCN.3 />
        <XCN.4 />
        <XCN.5 />
        <XCN.6 />
      </PV1.7>
      <PV1.9>
        <XCN.1>1812</XCN.1>
        <XCN.2>
          <FN.1>O BRIEN</FN.1>
        </XCN.2>
        <XCN.3>PETE</XCN.3>
        <XCN.4></XCN.4>
        <XCN.5></XCN.5>
        <XCN.6>PROF.</XCN.6>
      </PV1.9>
      <PV1.14 />
      <PV1.15 />
      <PV1.19>
        <CX.1 />
      </PV1.19>
      <PV1.36 />
      <PV1.37>
        <DLD.1></DLD.1>
      </PV1.37>
      <PV1.44>
        <TS.1 />
      </PV1.44>
      <PV1.45>
        <TS.1 />
      </PV1.45>
      <PV1.51>V</PV1.51>
    </PV1>
  </SIU_S12.PATIENT>
  <SIU_S12.RESOURCE>
    <RGS>
      <RGS.1 />
      <RGS.2 />
      <RGS.3>
        <CE.1 />
        <CE.2 />
        <CE.3 />
      </RGS.3>
    </RGS>
  </SIU_S12.RESOURCE>
</SIU_S12>"""

# ============================================================================
# CHANGES MADE TO SIU_S12.txt
# ============================================================================

CHANGES_SIU_S12 = """
CORRECTIONS MADE TO SIU_S12.txt:

1. Fixed SCH-2.4 (Universal ID Type)
   - BEFORE: <EI.4>HIPEHOS</EI.4>
   - AFTER:  <EI.4>L</EI.4>
   - REASON: "HIPEHOS" is not a valid HL7 table 0301 code. Changed to "L" (Local) 
             which is the correct code for a locally-defined identifier.

2. Added SCH-20 (Entered By Person) - MANDATORY field
   - ADDED:
     <SCH.20>
       <XCN.1>ADMIN001</XCN.1>
       <XCN.2>
         <FN.1>ADMIN</FN.1>
       </XCN.2>
       <XCN.3>STAFF</XCN.3>
       <XCN.4></XCN.4>
       <XCN.5></XCN.5>
       <XCN.6></XCN.6>
     </SCH.20>
   - REASON: This is a MANDATORY field that identifies who entered the appointment.
             Added generic admin staff member as the person who entered it.
             In production, this should be the actual staff member ID and name.

VALIDATION STATUS: Should now pass all MANDATORY checks.
"""

if __name__ == '__main__':
    print("=" * 80)
    print("HL7 MESSAGE ERROR ANALYSIS")
    print("=" * 80)
    
    print("\n" + "=" * 80)
    print("SIU_S12.txt - ERRORS FOUND")
    print("=" * 80)
    
    for error in ERRORS_SIU_S12:
        print(f"\nERROR #{error['error_id']}: {error['priority']}")
        print("-" * 80)
        print(error['plain_language'])
        print(f"FIX: {error['fix']}")
    
    print("\n" + "=" * 80)
    print("CORRECTED VERSION")
    print("=" * 80)
    print(CHANGES_SIU_S12)
