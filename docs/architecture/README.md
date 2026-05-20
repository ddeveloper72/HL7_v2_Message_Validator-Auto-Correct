# Architecture Diagrams

This folder contains architecture and flow diagrams for the HL7 v2 Message Validator application.

## Required Diagrams

### 1. target_architecture.png
**Main system architecture diagram**

Should show:
- Browser/User interface layer
- Flask application layer (with separation for Local vs Production modes)
- Data persistence layer (file storage vs Azure SQL)
- External services (Gazelle EVS API, Azure AD)
- Network connections and protocols

### 2. upload_flow.png
**File Upload & Validation Flow**

Should illustrate:
1. User uploads HL7 XML file via web interface
2. File saved to temporary storage
3. System sends Base64-encoded content to Gazelle EVS API
4. API returns validation OID and privacy key
5. System polls for validation results
6. Results displayed to user with error/warning counts

### 3. correction_flow.png
**Auto-Correction Workflow**

Should illustrate:
1. Validation detects errors in HL7 message
2. Auto-correction engine analyzes error types
3. System applies corrections (BOM removal, field fixes, code validation)
4. Corrected file saved to processed/ folder
5. Re-validation against Gazelle EVS
6. Display before/after comparison to user

### 4. pdf_flow.png
**PDF Report Generation Flow**

Should illustrate:
1. User clicks "Export PDF" on validation result
2. System extracts validation data (errors, warnings, metadata)
3. ReportLab generates formatted PDF document
4. PDF includes: header, summary table, error details, corrections applied
5. PDF downloaded to user's browser

### 5. auth_flow.png
**User Authentication Flow (Production Mode)**

Should illustrate:
1. User accesses application
2. Redirect to Azure AD login page
3. User authenticates with Microsoft credentials
4. Azure AD returns OAuth2 authorization code
5. Application exchanges code for access token
6. User profile created/updated in Azure SQL Database
7. Session established, redirect to dashboard

### 6. api_key_flow.png
**API Key Management Flow**

Should illustrate:
1. User navigates to Profile page
2. User enters Gazelle API key and validity dates
3. System validates date format and business rules
4. API key encrypted using Fernet (AES-256)
5. Encrypted key + validity dates stored in Azure SQL Database
6. Dashboard checks expiration and displays warning badges
7. Validation requests use decrypted API key from database

## Design Guidelines

- Use consistent color coding across diagrams
- Show data flow direction with arrows
- Include protocols/ports where relevant (HTTP/HTTPS, TDS)
- Distinguish between Local and Production modes where applicable
- Use icons for: browser, database, cloud services, security
- Keep diagrams clean and focused on core flow

## Tools

Recommended tools for creating diagrams:
- **draw.io (diagrams.net)** - Free, web-based
- **Lucidchart** - Professional diagramming
- **Microsoft Visio** - Enterprise standard
- **PlantUML** - Code-based diagrams
- **Excalidraw** - Hand-drawn style
