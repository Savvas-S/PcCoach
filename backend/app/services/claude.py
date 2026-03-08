import json
from functools import lru_cache

import anthropic

from app.config import settings
from app.models.builder import BuildRequest, ComponentRecommendation, DowngradeSuggestion, UpgradeSuggestion
from app.prompts.manager import build_system_prompt

_MODEL = "claude-sonnet-4-6"
_TIMEOUT = 60.0

BUILD_TOOL = {
    "name": "recommend_build",
    "description": "Return a structured PC build recommendation with components and affiliate links",
    "input_schema": {
        "type": "object",
        "properties": {
            "summary": {
                "type": "string",
                "description": "2-3 sentence explanation of the build choices and why they fit the user's needs",
            },
            "components": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {
                            "type": "string",
                            "enum": [
                                "cpu", "gpu", "motherboard", "ram", "storage",
                                "psu", "case", "cooling", "monitor", "keyboard", "mouse",
                            ],
                        },
                        "name": {"type": "string"},
                        "brand": {"type": "string"},
                        "price_eur": {"type": "number"},
                        "specs": {
                            "type": "object",
                            "additionalProperties": {"type": "string"},
                        },
                        "affiliate_url": {"type": "string", "format": "uri"},
                        "affiliate_source": {
                            "type": "string",
                            "enum": ["computeruniverse", "caseking", "amazon"],
                        },
                    },
                    "required": ["category", "name", "brand", "price_eur", "specs", "affiliate_url", "affiliate_source"],
                },
            },
        },
        "upgrade_suggestion": {
            "type": "object",
            "description": "Optional single-component upgrade if it meaningfully improves the build for under €75 extra",
            "properties": {
                "component_category": {
                    "type": "string",
                    "enum": ["cpu", "gpu"],
                },
                "current_name": {"type": "string"},
                "upgrade_name": {"type": "string"},
                "extra_cost_eur": {"type": "number"},
                "reason": {
                    "type": "string",
                    "description": "One sentence explaining why the upgrade is worth it",
                },
                "affiliate_url": {"type": "string", "format": "uri"},
                "affiliate_source": {
                    "type": "string",
                    "enum": ["computeruniverse", "caseking", "amazon"],
                },
            },
            "required": ["component_category", "current_name", "upgrade_name", "extra_cost_eur", "reason", "affiliate_url", "affiliate_source"],
        },
        "downgrade_suggestion": {
            "type": "object",
            "description": "Optional single-component downgrade that saves money while still adequately meeting the use case",
            "properties": {
                "component_category": {
                    "type": "string",
                    "enum": ["cpu", "gpu", "psu", "storage"],
                },
                "current_name": {"type": "string"},
                "downgrade_name": {"type": "string"},
                "savings_eur": {"type": "number"},
                "reason": {
                    "type": "string",
                    "description": "One sentence explaining the trade-off — what is saved and what is slightly compromised",
                },
                "affiliate_url": {"type": "string", "format": "uri"},
                "affiliate_source": {
                    "type": "string",
                    "enum": ["computeruniverse", "caseking", "amazon"],
                },
            },
            "required": ["component_category", "current_name", "downgrade_name", "savings_eur", "reason", "affiliate_url", "affiliate_source"],
        },
        "required": ["summary", "components"],
    },
}


class ClaudeService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=_TIMEOUT)
        self.model = _MODEL

    async def generate_build(self, request: BuildRequest) -> tuple[list[ComponentRecommendation], str, UpgradeSuggestion | None, DowngradeSuggestion | None]:
        user_message = f"""Please recommend a PC build for the following requirements:

        - Goal: {request.goal.value}
        - Budget: {request.budget_range.value} EUR
        - Form factor: {request.form_factor.value}
        - CPU brand preference: {request.cpu_brand.value}
        - GPU brand preference: {request.gpu_brand.value}
        - Cooling preference: {request.cooling_preference.value}
        - Include peripherals: {request.include_peripherals}
        - Parts already owned (exclude these): {[p.value for p in request.existing_parts] or 'none'}
        - Additional notes: {request.notes or 'none'}"""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=[{"type": "text", "text": build_system_prompt(), "cache_control": {"type": "ephemeral"}}],
            tools=[BUILD_TOOL],
            tool_choice={"type": "tool", "name": "recommend_build"},
            messages=[{"role": "user", "content": user_message}],
        )

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use:
            raise ValueError("No tool_use block in Claude response")
        data = tool_use.input if isinstance(tool_use.input, dict) else json.loads(tool_use.input)

        components = [ComponentRecommendation(**c) for c in data["components"]]
        summary = data["summary"]
        upgrade_suggestion = (
            UpgradeSuggestion(**data["upgrade_suggestion"])
            if data.get("upgrade_suggestion")
            else None
        )
        downgrade_suggestion = (
            DowngradeSuggestion(**data["downgrade_suggestion"])
            if data.get("downgrade_suggestion")
            else None
        )

        return components, summary, upgrade_suggestion, downgrade_suggestion


@lru_cache(maxsize=1)
def get_claude_service() -> ClaudeService:
    return ClaudeService()
