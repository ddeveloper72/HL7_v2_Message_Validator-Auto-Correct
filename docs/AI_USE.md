# AI Use and Transparency

## Development assistance

Generative AI tools have assisted with parts of this project, including:

- drafting and refactoring source code;
- diagnosing application and browser errors;
- redesigning the user interface;
- suggesting tests and verification steps;
- preparing and revising documentation.

AI assistance does not replace maintainer responsibility. Suggested changes are reviewed, adapted, and accepted by the project maintainer. Contributors should treat AI-generated code and prose like any other external contribution: verify it against the source, requirements, security model, and representative test data.

## Runtime behavior

The application's auto-correction engine is deterministic and rule-based. It uses explicit structural rules and configured HL7 code tables. It does not ask a generative AI model to interpret patient data or choose message corrections at runtime.

Messages are submitted to the configured Gazelle EVS service for validation. That external processing is separate from the generative AI tools used during software development.

## Review expectations

- Review every corrected message before production or clinical use.
- Confirm changes against the applicable Healthlink profile and Gazelle report.
- Use synthetic or approved test data during development.
- Do not provide credentials, secrets, or identifiable patient data to generative AI tools.
- Record material changes to correction rules and code tables.
- Use human review for security-sensitive, privacy-sensitive, and clinically relevant behavior.

## Limitations

AI-assisted development can introduce incorrect assumptions, insecure patterns, stale guidance, or incomplete edge-case handling. Inclusion in this repository does not prove that a suggestion was correct or independently validated.

The application is intended to support message validation and quality improvement. It does not provide clinical advice and should not be treated as an autonomous decision-making system.

## Updating this disclosure

Update this document if generative AI becomes part of the deployed runtime, if message content is sent to an AI service, or if the role of AI materially changes. Such a change should also be reflected in the privacy, security, and user-facing documentation before release.
