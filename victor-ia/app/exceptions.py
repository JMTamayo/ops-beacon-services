"""Domain errors surfaced as HTTP Problem Details."""


class AgentError(Exception):
    """Agent pipeline failed; mapped to 502/500 + RFC 7807."""

    def __init__(self, detail: str, *, status_code: int = 502) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code
