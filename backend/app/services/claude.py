import html
from functools import lru_cache

import anthropic

from app.config import settings
from app.models.builder import BuildRequest, ComponentRecommendation, ComponentSearchRequest, ComponentSearchResult, DowngradeSuggestion, StoreLink, UpgradeSuggestion
from app.prompts.manager import build_system_prompt, search_system_prompt

_TIMEOUT = 90.0

SEARCH_TOOL = {
    "name": "recommend_component",
    "description": "Return the best single component matching the user's description with search links to all three stores",
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Specific product name, e.g. 'AMD Ryzen 5 7600X'"},
            "brand": {"type": "string"},
            "estimated_price_eur": {"type": "number", "minimum": 0.01, "description": "Best estimate of current EUR price"},
            "reason": {"type": "string", "description": "2-3 sentences explaining why this component best matches the request"},
            "specs": {
                "type": "object",
                "additionalProperties": {"type": "string"},
            },
            "store_links": {
                "type": "array",
                "description": "Search links for this exact product at all three stores",
                "items": {
                    "type": "object",
                    "properties": {
                        "store": {"type": "string", "enum": ["computeruniverse", "caseking", "amazon"]},
                        "url": {"type": "string", "format": "uri"},
                    },
                    "required": ["store", "url"],
                },
            },
        },
        "required": ["name", "brand", "estimated_price_eur", "reason", "specs", "store_links"],
    },
}

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
                        "price_eur": {"type": "number", "minimum": 0.01},
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
                    "extra_cost_eur": {"type": "number", "minimum": 0.01},
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
                    "savings_eur": {"type": "number", "minimum": 0.01},
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
        },
        "required": ["summary", "components"],
    },
}


class ClaudeService:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key, timeout=_TIMEOUT)
        self.model = settings.claude_model

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
        - Additional notes: {html.escape(request.notes) if request.notes else 'none'}"""

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
        data = tool_use.input

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

    async def search_component(self, request: ComponentSearchRequest) -> ComponentSearchResult:
        user_message = f"""Category: {request.category.value}
You must recommend a {request.category.value}. Do not recommend any other component type.

User description:
{html.escape(request.description)}"""

        response = await self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            system=[{"type": "text", "text": search_system_prompt(), "cache_control": {"type": "ephemeral"}}],
            tools=[SEARCH_TOOL],
            tool_choice={"type": "tool", "name": "recommend_component"},
            messages=[{"role": "user", "content": user_message}],
        )

        tool_use = next((b for b in response.content if b.type == "tool_use"), None)
        if not tool_use:
            raise ValueError("No tool_use block in Claude response")
        data = tool_use.input

        return ComponentSearchResult(
            name=data["name"],
            brand=data["brand"],
            category=request.category,
            estimated_price_eur=data["estimated_price_eur"],
            reason=data["reason"],
            specs=data.get("specs", {}),
            store_links=[StoreLink(**s) for s in data.get("store_links", [])],
        )


@lru_cache(maxsize=1)
def get_claude_service() -> ClaudeService:
    return ClaudeService()
