# Architecture Diagrams

This folder contains architecture and flow diagram specifications for the HL7 v2 Message Validator application.

## Diagram Format

All architecture diagrams are created using **Mermaid**, a text-based diagramming tool that renders directly in GitHub, GitLab, VS Code, and many other markdown viewers.

### Benefits of Mermaid
- ✅ **Version Controlled** - Diagrams are plain text in the README
- ✅ **Easy to Edit** - No specialized tools required
- ✅ **Auto-Rendering** - GitHub renders automatically
- ✅ **Always in Sync** - Diagrams live alongside code
- ✅ **Accessible** - Screen reader friendly
- ✅ **Collaborative** - Easy to review in pull requests

## Diagrams Included

All diagrams are embedded directly in the main [README.md](../../README.md) under the "🏗️ Target Architecture" section.

### System Architecture Diagrams

#### 1. Local Mode Architecture
**Mermaid Type:** `flowchart TB`

Shows:
- User browser interface
- Flask application components (UI, Engine, PDF, Session, Storage)
- Connection to Gazelle EVS API
- HTTP protocol flow

#### 2. Production Mode Architecture
**Mermaid Type:** `flowchart TB`

Shows:
- User browser with HTTPS
- Azure AD authentication layer
- Flask application components (Auth, Session, UI, Engine, PDF)
- Data persistence (API Store, Profile, History, Stats)
- External services (Azure AD, Gazelle EVS, Azure SQL)
- OAuth2 and TDS protocol connections

### Operational Flow Diagrams

#### 3. File Upload & Validation Flow
**Mermaid Type:** `sequenceDiagram`

Illustrates:
1. User uploads HL7 XML file
2. File saved to temporary storage
3. Message type detection
4. Base64 encoding and Gazelle submission
5. Polling for validation results
6. Display of validation report

#### 4. Auto-Correction Workflow
**Mermaid Type:** `flowchart TB`

Illustrates decision tree:
1. Validation failure analysis
2. BOM removal check
3. XML declaration fixes
4. Code table validation
5. Required field population
6. Segment reordering
7. Field length truncation
8. Save and re-validation
9. Success or partial correction result

#### 5. PDF Report Generation Flow
**Mermaid Type:** `sequenceDiagram`

Illustrates:
1. User clicks "Export PDF"
2. Flask retrieves validation data
3. ReportLab creates PDF components (header, summary, errors, corrections)
4. PDF buffer returned
5. Browser downloads PDF

#### 6. User Authentication Flow (Production Mode)
**Mermaid Type:** `sequenceDiagram`

Illustrates OAuth2 flow:
1. User accesses application
2. Session check and redirect to landing
3. Login button click
4. Azure AD OAuth2 authorization
5. User credentials entry
6. Authorization code exchange
7. Access token retrieval
8. User profile creation/update in database
9. Session establishment
10. Dashboard redirect

#### 7. API Key Management Flow
**Mermaid Type:** `sequenceDiagram`

Illustrates:
1. User navigates to profile
2. Existing dates loaded from database
3. User enters API key + validity dates
4. Date validation (format, business rules)
5. Fernet encryption (AES-256)
6. Database update with encrypted key and dates
7. Audit log entry
8. Dashboard displays expiration status with badge

### Security and Deployment Diagrams

#### 8. Security Architecture
**Mermaid Type:** `flowchart LR`

Shows layered security:
- CSRF Protection
- Rate Limiting
- Input Sanitization
- SQL Injection Prevention
- Encrypted Sessions
- API Key Encryption
- HTTPS/TLS
- Secure Headers

#### 9. Docker Deployment
**Mermaid Type:** `flowchart TB`

Shows:
- Docker Host container
- Gunicorn WSGI server
- Flask application
- FreeTDS driver
- Health endpoint
- Volume mounts (uploads, processed, sessions)
- External Azure SQL connection

#### 10. Heroku Deployment
**Mermaid Type:** `flowchart TB`

Shows:
- Heroku web dyno
- Gunicorn process
- Python runtime
- FreeTDS via Aptfile
- Buildpacks (Python, FreeTDS)
- Config vars injection
- External services (Azure SQL, Gazelle EVS)

## Editing Diagrams

### Viewing Locally
1. **VS Code** - Install "Markdown Preview Mermaid Support" extension
2. **Browser** - Use [Mermaid Live Editor](https://mermaid.live/)
3. **CLI** - Use [mermaid-cli](https://github.com/mermaid-js/mermaid-cli)

### Editing Workflow
1. Find the diagram in [README.md](../../README.md)
2. Locate the mermaid code block
3. Edit the Mermaid syntax
4. Preview in VS Code or paste into Mermaid Live Editor
5. Commit changes

### Mermaid Resources
- [Official Documentation](https://mermaid.js.org/)
- [Flowchart Syntax](https://mermaid.js.org/syntax/flowchart.html)
- [Sequence Diagram Syntax](https://mermaid.js.org/syntax/sequenceDiagram.html)
- [Mermaid Live Editor](https://mermaid.live/)
- [Theme Configuration](https://mermaid.js.org/config/theming.html)
