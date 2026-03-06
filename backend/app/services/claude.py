import anthropic
from functools import lru_cache

from app.config import settings


class ClaudeService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        self.model = "claude-sonnet-4-6"

    async def chat(self, messages: list[dict], system: str | None = None) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system or "You are PcCoach, an expert PC building assistant. Help users choose the right components based on their requirements and budget.",
            messages=messages,
        )
        return response.content[0].text


@lru_cache(maxsize=1)
def get_claude_service() -> ClaudeService:
    return ClaudeService()
