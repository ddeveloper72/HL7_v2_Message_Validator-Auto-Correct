# Documentation

This directory contains the maintained technical documentation for the HL7 v2 Message Validator and Auto-Corrector.

## Start here

- [Project README](../README.md): overview, setup, configuration, architecture, and troubleshooting.
- [AI use](AI_USE.md): disclosure of AI-assisted development and runtime boundaries.
- [Architecture diagrams](architecture/README.md): diagram scope and editing guidance.

## Setup and operations

The following maintained guides remain at the repository root because they are commonly used during setup:

- [Local development](../LOCAL_DEVELOPMENT_GUIDE.md)
- [Docker quick start](../DOCKER_QUICK_START.md)
- [Docker configuration](../DOCKER_CONFIGURATION.md)
- [Docker deployment](../DOCKER_DEPLOYMENT.md)
- [Docker mode reference](../DOCKER_MODE.md)
- [Azure requirements](../AZURE_REQUIREMENTS.md)

## Historical documents

`docs/archive/` contains implementation notes, deployment reports, and feature-completion records from earlier versions. These files are retained for traceability but may describe obsolete behavior, interfaces, or deployment state.

When archived material conflicts with the project README or current source code, use the current source code and maintained documentation.

## Documentation standards

- Use plain, descriptive headings without decorative symbols.
- Prefer exact commands and configuration names over narrative shortcuts.
- Do not include credentials, API keys, connection strings, or real patient data.
- Distinguish current behavior from planned or historical behavior.
- Document verification steps and known limitations.
- Update links when files are renamed or moved.
