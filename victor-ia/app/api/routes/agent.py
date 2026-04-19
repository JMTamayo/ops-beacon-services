from fastapi import APIRouter, Depends, HTTPException

from app.api.security.api_key import get_api_key
from app.domain.agent import VictorIA
from app.exceptions import AgentError
from app.models.agent import VictorIAChatRequest, VictorIAChatResponse

_victor = VictorIA()

agent_router = APIRouter(
    prefix="/victor-ia",
    tags=["Agent"],
)


@agent_router.post(
    path="/",
    response_model=VictorIAChatResponse,
    summary="Chat with Victor IA",
    dependencies=[Depends(get_api_key)],
    responses={
        401: {"description": "Missing or invalid API key (RFC 7807 problem+json)."},
        422: {"description": "Validation error (RFC 7807 problem+json)."},
        502: {"description": "Agent or upstream LLM failure (RFC 7807 problem+json)."},
    },
)
async def ask(body: VictorIAChatRequest) -> VictorIAChatResponse:
    try:
        content = await _victor.complete(body.message)
    except AgentError as e:
        raise HTTPException(status_code=e.status_code, detail=e.detail) from e
    return VictorIAChatResponse(content=content)
