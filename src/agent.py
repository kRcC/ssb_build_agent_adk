from __future__ import annotations

import asyncio
import os
import uuid
import warnings
from typing import Any

from dotenv import load_dotenv

from google.adk.agents.llm_agent import Agent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.tools import AgentTool
from google.adk.tools.mcp_tool import McpToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from mcp_client import DEFAULT_MCP_URL

load_dotenv()
warnings.filterwarnings("ignore")

APP_NAME = "ssb_build_agent"
USER_ID = "streamlit_user"
MODEL_NAME = os.getenv("GOOGLE_ADK_MODEL", "gemini-2.5-flash")
MCP_URL = os.getenv("MCP_URL", DEFAULT_MCP_URL)


# Koble til FastMCP-serveren
_toolset = McpToolset(
    connection_params=StreamableHTTPConnectionParams(url=MCP_URL),
)

_input_agent = Agent(
    model=MODEL_NAME,
    name="input_agent",
    description="Parser bruker-spørsmål om norske kommuner og byggesaker til strukturert form.",
    instruction=r"""Du analyserer bruker-spørsmål om norske kommuner for boligutvikling.
Oppgaver:
1. Identifiser intent: sammenlign (2+ kommuner), beste (beste kandidat), vurder (en/få kommuner), default (ranking alle)
2. Ekstrahér kommune-navn fra spørsmålet
3. Emitter strukturert spørring som JSON: {"intent": "...", "municipalities": [...], "question": "..."}
Svar KUN med JSON-strukturen, ingen annet tekst.""",
    output_key="structured_question",
)

_retriever_agent = Agent(
    model=MODEL_NAME,
    name="retriever_agent",
    description="Henter SSB-data om kommuner via MCP-tools basert på brukers spørring.",
    instruction=r"""Du henter data for norske kommuner ved hjelp av disse verktøyene:
- get_population_data_tool
- get_building_case_data_tool
- get_best_building_candidate_tool (for "beste" intent)
- compare_municipalities_tool (for "sammenlign" intent)
- rank_municipalities_tool (for rangering)
- summarize_municipality_tool (for enkeltkommune)
- get_llm_context_tool (for full kontekst)

Input: {structured_question}
Bruk riktig verktøy basert på intent. Ikke finn på data – bruk kun tool-resultater.
Output: {"status": "success"|"error", "data": {...}}""",
    tools=[_toolset],
    output_key="retrieved_data",
)

_presenting_agent = Agent(
    model=MODEL_NAME,
    name="presenting_agent",
    description="Formaterer hentede data til kort, leselig norsk tekst for bruker.",
    instruction=r"""Gjør dataene leselige for brukeren:
- Hvis data mangler eller er ufullstendig: kort forklaring av hva som mangler
- Hvis data er tilgjengelig: 3-6 linjer klart norsk, med:
   - Hovedanbefaling eller direkte svar på spørsmålet
   - Nøkkeltall (avrundet, ikke for mange desimaler)
   - Kort bakgrunnsbegrunnelse hvis relevant

Format: Uten markdown-headers, ren tekst. Vær konkret og praktisk.""",
    output_key="final_answer",
)


# ===== SEKVENSIELL AGENT =====

_sequential_agent = SequentialAgent(
    name="ssb_sequential_workflow",
    sub_agents=[_input_agent, _retriever_agent, _presenting_agent],
    description="Analyserer brukers spørsmål gjennom strukturering → datahenting → presentasjon.",
)

_question_tool = AgentTool(agent=_sequential_agent)


# ===== ROOT-AGENT =====

root_agent = Agent(
    model=MODEL_NAME,
    name="root_agent",
    description="Koordinerer spørsmål om norske kommuner og boligutvikling.",
    instruction=r"""Du er en kortfattet koordinator for spørsmål om norske kommuner.

Hvis brukeren spør om norske kommuner, boligutvikling eller byggesaker:
- Kall question_tool med spørsmålet
- Returner NØYAKTIG svaret fra question_tool, uten endringer

Hvis spørsmålet er urelatert:
- Svar: "Jeg hjelper kun med spørsmål om norske kommuner og boligutvikling." """,
    tools=[_question_tool],
)

_session_service = InMemorySessionService()
_runner = Runner(agent=root_agent, app_name=APP_NAME, session_service=_session_service)




def _unwrap_agent_response(content: Any) -> str:
    """Hent tekst fra agent-respons."""
    if hasattr(content, "parts") and content.parts:
        for part in content.parts:
            if hasattr(part, "text") and part.text:
                return part.text
    if isinstance(content, str):
        return content
    return ""


async def _run_agent_async(question: str) -> str:
    """Kjør sekvensiell workflow: input → retriever → presenting."""
    session_id = f"session_{uuid.uuid4().hex}"
    await _session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id,
    )

    try:
        message = types.Content(role="user", parts=[types.Part(text=question)])

        final_text = ""
        async for event in _runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=message,
        ):
            if event.is_final_response() and event.content:
                final_text = _unwrap_agent_response(event.content)

        return final_text or "Agenten ga ikke svar."

    except Exception as e:
        error_msg = str(e)
        if "MCP" in error_msg or "127.0.0.1:8000" in error_msg:
            return (
                f"Klarte ikke koble til MCP-server på {MCP_URL}. "
                "Start serveren med: python -m mcp_server.server"
            )
        return f"Feil ved kjøring av agent: {e}"



def answer_question(question: str) -> str:
    """Svar på spørsmål via sekvensiell agent-workflow (offentlig inngang)."""
    if not os.getenv("GOOGLE_API_KEY"):
        return "Mangler GOOGLE_API_KEY i .env"

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_run_agent_async(question))
    except RuntimeError as e:
        return str(e)
    except Exception as e:
        return f"Feil: {e}"
    finally:
        loop.close()

