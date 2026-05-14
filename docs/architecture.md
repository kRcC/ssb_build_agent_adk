# Arkitektur

```mermaid
flowchart TD
    A[Bruker] --> B[Streamlit app]
    B --> C{Agentmodus}
    C --> D[Regelbasert agent]
    C --> E[Google ADK OrchestratorAgent]
    D --> F[Python tools]
    E --> F
    F --> G[Analysis.py]
    G --> H[Transform.py]
    H --> I[SSB Client]
    I --> J[SSB API]
    F --> K[MCP Server]
```

## Agentroller

- OrchestratorAgent: velger arbeidsflyt og svarformat.
- DataAgent: representert av SSB tools.
- AnalysisAgent: representert av analysefunksjoner.
- ReportAgent: ADK-agenten formulerer svaret.
