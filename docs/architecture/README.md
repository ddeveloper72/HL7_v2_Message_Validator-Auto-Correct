# Architecture diagrams

The primary architecture diagram is embedded in the main [project README](../../README.md). It uses Mermaid so that the diagram remains version controlled and renders directly in GitHub and compatible Markdown viewers.

## Diagram scope

The current diagram covers:

- the browser and Flask dashboard;
- server-side sessions and temporary file storage;
- Gazelle EVS validation;
- the deterministic correction and revalidation loop;
- PDF report generation;
- optional Microsoft Entra ID authentication;
- optional Azure SQL persistence.

Detailed sequence behavior is described in the README's "How it works" section and in the source routes in `dashboard_app.py`.

## Editing the diagram

1. Open [README.md](../../README.md).
2. Locate the fenced `mermaid` block in the Architecture section.
3. Update the diagram together with the behavior or component it describes.
4. Preview the Markdown in GitHub, VS Code, or the [Mermaid Live Editor](https://mermaid.live/).
5. Check that labels remain readable without relying on colour alone.

## Conventions

- Keep diagrams focused on stable components and boundaries.
- Use names that match files, services, and configuration used by the application.
- Avoid embedding credentials, host-specific identifiers, or patient information.
- Prefer one current diagram over several near-duplicate historical diagrams.

## Resources

- [Mermaid documentation](https://mermaid.js.org/)
- [Flowchart syntax](https://mermaid.js.org/syntax/flowchart.html)
- [Sequence diagram syntax](https://mermaid.js.org/syntax/sequenceDiagram.html)
