"""
Central registry of all LangChain tools.

Add a new integration:
1. Create `app/tools/<name>.py` with `@tool` functions and a `TOOLS_*` list.
2. Import and extend `build_tools()` below.
"""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.tools import BaseTool

from app.tools import ener_vault, teams_notify


def build_tools() -> list[BaseTool]:
    """Return every tool exposed to the agent (extend as integrations grow)."""
    tools: list[BaseTool] = []
    tools.extend(ener_vault.TOOLS_ENER_VAULT)
    tools.extend(teams_notify.TOOLS_TEAMS)
    return tools


ALL_TOOLS: Sequence[BaseTool] = build_tools()
