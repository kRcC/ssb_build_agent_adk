from __future__ import annotations

import argparse
import asyncio
import json
from typing import Any

from fastmcp import Client

DEFAULT_MCP_URL = "http://127.0.0.1:8000/mcp"


def _unwrap(response: Any) -> Any:
    if hasattr(response, "data") and response.data is not None:
        return response.data
    content = getattr(response, "content", None)
    if isinstance(content, list) and content and hasattr(content[0], "text"):
        return content[0].text
    return response


def _format(value: Any) -> str:
    value = _unwrap(value)
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, indent=2)
    return str(value)


async def call_tool(tool_name: str, arguments: dict[str, Any] | None = None, url: str = DEFAULT_MCP_URL) -> Any:
    async with Client(url) as client:
        return await client.call_tool(tool_name, arguments or {})


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["health", "healthcheck", "summary", "rank", "best", "context"])
    parser.add_argument("--url", default=DEFAULT_MCP_URL)
    args = parser.parse_args()

    tool_map = {
        "health": ("healthcheck", {}),
        "healthcheck": ("healthcheck", {}),
        "summary": ("get_data_summary_tool", {}),
        "rank": ("rank_municipalities_tool", {"limit": 5}),
        "best": ("get_best_building_candidate_tool", {}),
        "context": ("get_llm_context_tool", {"question": "Hvor bør jeg bygge bolig?"}),
    }

    tool_name, tool_args = tool_map[args.command]
    result = await call_tool(tool_name, tool_args, url=args.url)
    print(_format(result))


if __name__ == "__main__":
    asyncio.run(main())
