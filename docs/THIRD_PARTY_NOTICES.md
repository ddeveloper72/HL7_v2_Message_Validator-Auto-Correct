# Third-party notices and standards materials

This project includes and references third-party standards, services, libraries, and documentation. This notice is intended to preserve attribution and make redistribution considerations visible. It is not a legal opinion; confirm licence and redistribution permissions before publishing this repository or packaging it for external distribution.

## HL7 v2.4 standards materials

The repository contains HL7 v2.4 reference material under:

- `v24_PDF/`
- `HL7-xml_v2.4/`
- `hl7_code_tables.json`

These materials are used as implementation references for HL7 v2 message validation, XML structure, and deterministic code-table correction.

The XML schema files in `HL7-xml_v2.4/` include this embedded notice:

```text
Copyright (c) 1999-2016, Health Level Seven. All rights reserved.
```

The PDF set in `v24_PDF/` appears to be the HL7 Version 2.4 standard documentation set and includes `IP Copyright and Trademarks.pdf`. The PDFs and schemas should be treated as HL7-owned standards materials. Keep HL7 copyright and trademark notices with the files, do not remove attribution, and confirm that the project has the necessary rights before redistributing the PDFs, schemas, or derived code-table data outside authorised use.

Attribution:

- HL7, Health Level Seven, and HL7 Version 2 are standards and marks associated with Health Level Seven International.
- The included v2.4 standards documentation and v2 XML schema artifacts are credited to Health Level Seven.
- This project is not affiliated with, endorsed by, or certified by Health Level Seven International unless separately agreed in writing.

## Gazelle EVS and IHE

The application validates messages by submitting them to a configured Gazelle EVS endpoint, such as the eHealth Ireland testing service. Gazelle EVS is an external validation service and is not bundled with this project.

Attribution:

- Gazelle and EVS names are used descriptively to identify the external validation workflow.
- IHE and Gazelle-related names, services, and validation reports remain the property of their respective owners.
- This project is not affiliated with, endorsed by, or certified by IHE, Gazelle, or eHealth Ireland unless separately agreed in writing.

Operators are responsible for ensuring their use of Gazelle EVS complies with the relevant service terms, API-key terms, data-protection requirements, and clinical-data governance requirements.

## Frontend assets and CDN libraries

The user interface loads Tailwind Browser and Lucide icons from `cdn.jsdelivr.net` in the current templates and Content Security Policy. Those assets are third-party open-source projects distributed under their own licences.

Attribution:

- Tailwind CSS is provided by Tailwind Labs and contributors.
- Lucide icons are provided by the Lucide contributors.
- jsDelivr is used as a CDN provider for browser-loaded frontend assets.

If the application is packaged for offline or production use with vendored frontend assets, retain the relevant upstream licence notices alongside the vendored files.

## Python dependencies

Python dependencies are declared in `requirements.txt`. They are third-party packages distributed under their respective licences. Before external distribution, production packaging, or compliance review, generate and retain a dependency licence inventory from the locked dependency set used for deployment.

Typical packages used by this project include Flask, Requests, ReportLab, MSAL, Cryptography, Jinja2, Bleach, and related dependencies. Their licences are not replaced by this project notice.

## Project licence status

No standalone project licence file is currently included. Treat the repository as an internal project unless the owner provides separate licensing terms.

The presence of third-party standards materials, schemas, code tables, package dependencies, or service integrations does not grant additional rights beyond the terms provided by their respective owners.

