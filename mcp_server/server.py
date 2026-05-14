from __future__ import annotations

from datetime import datetime
from fastmcp import FastMCP

from src.tools import (
    get_population_data,
    get_building_case_data,
    get_data_summary,
    get_population_growth,
    get_case_processing_time,
    rank_municipalities,
    get_best_building_candidate,
    compare_municipalities,
    summarize_municipality,
    get_llm_context,
)

mcp = FastMCP("BuildSmart SSB MCP")


@mcp.tool()
def healthcheck() -> dict:
    return {"status": "ok", "server": "BuildSmart SSB MCP", "timestamp": datetime.now().isoformat()}


@mcp.tool()
def get_population_data_tool() -> dict:
    return get_population_data()


@mcp.tool()
def get_building_case_data_tool() -> dict:
    return get_building_case_data()


@mcp.tool()
def get_data_summary_tool() -> dict:
    return get_data_summary()


@mcp.tool()
def get_population_growth_tool(start_year: str = "2021", end_year: str = "2025") -> list[dict]:
    return get_population_growth(start_year=start_year, end_year=end_year)


@mcp.tool()
def get_case_processing_time_tool(year: str = "2025") -> list[dict]:
    return get_case_processing_time(year=year)


@mcp.tool()
def rank_municipalities_tool(start_year: str = "2021", end_year: str = "2025", limit: int = 10) -> list[dict]:
    return rank_municipalities(start_year=start_year, end_year=end_year, limit=limit)


@mcp.tool()
def get_best_building_candidate_tool() -> dict:
    return get_best_building_candidate()


@mcp.tool()
def compare_municipalities_tool(municipalities: list[str]) -> list[dict]:
    return compare_municipalities(municipalities)


@mcp.tool()
def summarize_municipality_tool(municipality: str) -> dict:
    return summarize_municipality(municipality)


@mcp.tool()
def get_llm_context_tool(question: str, top_n: int = 10) -> dict:
    return get_llm_context(question, top_n=top_n)


def start_server() -> None:
    # HTTP-endepunkt for eksterne MCP-clients.
    mcp.run(transport="http", host="127.0.0.1", port=8000, path="/mcp")


if __name__ == "__main__":
    start_server()
