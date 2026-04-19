"""Victor IA agent: LangGraph ReAct + tool registry."""

from __future__ import annotations

import logging
import re

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langgraph.prebuilt import create_react_agent

from app.config.conf import CONFIG
from app.exceptions import AgentError
from app.tools.registry import build_tools

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Victor IA, an assistant for the ops-beacon stack.
You can query and create devices (meters), list or fetch entities (load catalog), and create device–entity assignments (time windows) in ener-vault using your tools.
The TEAMS_WEBHOOK_URL integration exists only to **notify the operations team** (equipo de operación) in their Teams channel: alerts, escalations, or summaries that operations must see. If the user asks to notify Teams, alert operations, or inform the ops team, call teams_send_notification when TEAMS_WEBHOOK_URL is configured; do not treat it as a generic personal messaging endpoint.
Prefer calling tools instead of guessing. Summarize tool output clearly for the operator.
Answer in the same language as the user when possible.

Formatting: write in plain text only. Do not use Markdown or other markup (no headings with #, no bold/italic with * or _, no backticks, no bullet lists with - or *).

Output must be a single continuous line of prose: do not use line breaks, paragraph breaks, tabs, or list formatting. Use commas and periods only; the reply will be normalized to one line if needed."""


def _message_text(msg: BaseMessage) -> str:
    content = msg.content
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]))
            else:
                parts.append(str(block))
        return "".join(parts)
    return str(content)


def _single_line_response(text: str) -> str:
    """Collapse whitespace and line breaks into one space; strip ends."""

    t = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    t = t.replace("\u2028", " ").replace("\u2029", " ")
    t = re.sub(r"[ \t]+", " ", t).strip()
    return t


class VictorIA:
    """ReAct agent with pluggable tools."""

    def __init__(self) -> None:
        self._llm: BaseChatModel = init_chat_model(
            model=CONFIG.LLM_MODEL,
            model_provider=CONFIG.LLM_PROVIDER,
            temperature=CONFIG.LLM_TEMPERATURE,
            api_key=CONFIG.LLM_API_KEY.get_secret_value(),
        )
        tools = build_tools()
        self._graph = create_react_agent(
            self._llm,
            tools,
            prompt=SYSTEM_PROMPT,
        )

    async def complete(self, user_message: str) -> str:
        try:
            result = await self._graph.ainvoke({"messages": [HumanMessage(content=user_message)]})
            messages: list[BaseMessage] = list(result.get("messages") or [])

            for msg in reversed(messages):
                if not isinstance(msg, AIMessage):
                    continue
                body = _message_text(msg)
                if getattr(msg, "tool_calls", None) and not body.strip():
                    continue
                if body.strip():
                    return _single_line_response(body)

            raise AgentError(
                "The language model returned no usable assistant message.",
                status_code=502,
            )

        except AgentError:
            raise
        except Exception as e:
            logger.exception("Victor IA failure")
            raise AgentError(str(e), status_code=502) from e
