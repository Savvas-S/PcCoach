"""Output guardrails — run AFTER Claude responds, BEFORE sending to the client.

Responsibilities:
1. Schema enforcement: validate Claude's response matches BuildResult.
2. Off-topic detection: detect refusal / apology patterns.
3. Affiliate URL validation: strip non-allowlisted URLs and log them.
4. Price sanity: strip zero/negative/astronomical components; warn if total
   exceeds 150 % of the stated budget.
5. Content safety: strip PII (phone, email, external URLs); reject on
   system-prompt-leak phrases.

None of these checks raise Python exceptions — they return either a cleaned
``BuildResult`` or a sentinel ``GuardrailBlocked`` that callers translate to
the appropriate HTTP error.
"""

import logging
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from app.models.builder import (
    BudgetRange,
    BuildResult,
    ComponentRecommendation,
    ComponentSearchResult,
)

_log = logging.getLogger("security.output_guard")

# ---------------------------------------------------------------------------
# Allowlisted affiliate domains (must stay in sync with models/builder.py)
# ---------------------------------------------------------------------------
# Amazon-only for MVP — widen when new stores are added.
# Must stay in sync with models/builder.py and frontend/src/lib/url.ts.
_AFFILIATE_ALLOWED_HOSTS: frozenset[str] = frozenset(
    {
        "amazon.de",
        "www.amazon.de",
    }
)

# ---------------------------------------------------------------------------
# Off-topic / refusal detection
# ---------------------------------------------------------------------------
_REFUSAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in [
        r"\bI cannot\b",
        r"\bI can'?t\b",
        r"\bI'?m not able to\b",
        r"\bAs an AI\b",
        r"\bI don'?t have\b",
        r"\bI'?m sorry\b",
        r"\bI apologize\b",
        r"\bunable to (?:assist|help|provide)\b",
    ]
]

# ---------------------------------------------------------------------------
# System-prompt leak detection — reject the entire response if found
# ---------------------------------------------------------------------------
_LEAK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.I)
    for p in [
        r"your instructions? (?:are|say|tell)\b",
        r"\bsystem prompt\b",
        r"\bignore previous\b",
        r"\byou are (?:actually|really|secretly)\b",
    ]
]

# ---------------------------------------------------------------------------
# PII / external content patterns
# ---------------------------------------------------------------------------
_PHONE_PATTERN = re.compile(r"\+?\d[\d\s\-()]{7,}\d")
_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_URL_PATTERN = re.compile(r"https?://[^\s\"'<>]+")

# ---------------------------------------------------------------------------
# Price limits
# ---------------------------------------------------------------------------
_MAX_COMPONENT_PRICE = 50_000.0
_BUDGET_OVERAGE_RATIO = 1.5

# ---------------------------------------------------------------------------
# Budget range → rough numeric upper bound (used for overage check)
# ---------------------------------------------------------------------------
_BUDGET_UPPER: dict[BudgetRange, float] = {
    BudgetRange.range_0_1000: 1_000.0,
    BudgetRange.range_1000_1500: 1_500.0,
    BudgetRange.range_1500_2000: 2_000.0,
    BudgetRange.range_2000_3000: 3_000.0,
    BudgetRange.over_3000: 5_000.0,  # conservative estimate for overage check
}


# ---------------------------------------------------------------------------
# Sentinel returned when the guardrail blocks the response entirely
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class GuardrailBlocked:
    reason: str  # human-readable, for server-side logging only


class OutputGuardrail:
    """Cleans and validates a raw BuildResult from Claude."""

    def check(
        self,
        result: BuildResult,
        budget_range: BudgetRange,
    ) -> BuildResult | GuardrailBlocked:
        """Run all output checks.

        Returns:
            A (possibly mutated) ``BuildResult`` on success, or a
            ``GuardrailBlocked`` sentinel when the response must be rejected
            entirely.
        """
        # 1. System-prompt leak check — block immediately, before any mutation
        blocked = self._check_prompt_leak(result)
        if blocked:
            return blocked

        # 2. Off-topic / refusal detection
        blocked = self._check_off_topic(result)
        if blocked:
            return blocked

        # 3. Affiliate URL validation (strips bad URLs in-place)
        result = self._sanitize_affiliate_urls(result)

        # 4. Price sanity (strips bad components, adds warnings)
        result = self._check_prices(result, budget_range)

        # 5. Content safety (strip PII / external URLs from text fields)
        result = self._strip_pii(result)

        return result

    # ------------------------------------------------------------------
    # Internal checks
    # ------------------------------------------------------------------

    def _check_prompt_leak(self, result: BuildResult) -> GuardrailBlocked | None:
        combined = _combined_text(result)
        for pattern in _LEAK_PATTERNS:
            if pattern.search(combined):
                _log.error(
                    "output_guard: system-prompt leak detected pattern=%s",
                    pattern.pattern[:40],
                )
                return GuardrailBlocked(reason="system_prompt_leak")
        return None

    def _check_off_topic(self, result: BuildResult) -> GuardrailBlocked | None:
        combined = _combined_text(result)
        for pattern in _REFUSAL_PATTERNS:
            if pattern.search(combined):
                _log.warning(
                    "output_guard: off-topic/refusal response detected pattern=%s",
                    pattern.pattern[:40],
                )
                return GuardrailBlocked(reason="off_topic_response")
        return None

    def _sanitize_affiliate_urls(self, result: BuildResult) -> BuildResult:
        clean_components: list[ComponentRecommendation] = []
        for comp in result.components:
            if comp.affiliate_url is not None:
                host = urlparse(str(comp.affiliate_url)).hostname or ""
                if host not in _AFFILIATE_ALLOWED_HOSTS:
                    _log.warning(
                        "output_guard: stripped non-allowlisted affiliate URL "
                        "category=%s host=%s",
                        comp.category.value,
                        host,
                    )
                    # Rebuild without the bad URL using model_copy
                    comp = comp.model_copy(
                        update={"affiliate_url": None, "affiliate_source": None}
                    )
            clean_components.append(comp)
        return result.model_copy(update={"components": clean_components})

    def _check_prices(
        self, result: BuildResult, budget_range: BudgetRange
    ) -> BuildResult:
        warnings: list[str] = list(result.warnings)
        clean: list[ComponentRecommendation] = []

        for comp in result.components:
            if comp.price_eur <= 0 or comp.price_eur > _MAX_COMPONENT_PRICE:
                _log.warning(
                    "output_guard: stripped component with invalid price "
                    "category=%s price=%.2f",
                    comp.category.value,
                    comp.price_eur,
                )
                continue  # strip the component
            clean.append(comp)

        total = sum(c.price_eur for c in clean)
        budget_upper = _BUDGET_UPPER.get(budget_range, 3_000.0)
        if total > budget_upper * _BUDGET_OVERAGE_RATIO:
            _log.warning(
                "output_guard: build total %.2f exceeds 150%% of budget upper %.2f",
                total,
                budget_upper,
            )
            warnings.append("Recommended build exceeds your stated budget")

        # model_copy does NOT re-run @model_validator, so total_price_eur would
        # be stale if components were stripped.  Recompute it explicitly.
        return result.model_copy(
            update={
                "components": clean,
                "total_price_eur": total if clean else None,
                "warnings": warnings,
            }
        )

    def check_search(
        self,
        result: ComponentSearchResult,
    ) -> ComponentSearchResult | GuardrailBlocked:
        """Run output checks on a search response.

        Applies leak detection, off-topic detection, and PII stripping to the
        free-text fields.  Store link URLs are validated by the StoreLink
        Pydantic model, so URL allowlist enforcement is already handled there.
        """
        combined = f"{result.name} {result.brand} {result.reason}"

        # 1. System-prompt leak — block entirely
        for pattern in _LEAK_PATTERNS:
            if pattern.search(combined):
                _log.error(
                    "output_guard: system-prompt leak in search response pattern=%s",
                    pattern.pattern[:40],
                )
                return GuardrailBlocked(reason="system_prompt_leak")

        # 2. Off-topic / refusal
        for pattern in _REFUSAL_PATTERNS:
            if pattern.search(combined):
                _log.warning(
                    "output_guard: off-topic response in search pattern=%s",
                    pattern.pattern[:40],
                )
                return GuardrailBlocked(reason="off_topic_response")

        # 3. PII strip from text fields
        clean_reason = _strip_pii_from_text(result.reason)
        if clean_reason != result.reason:
            result = result.model_copy(update={"reason": clean_reason})

        return result

    def _strip_pii(self, result: BuildResult) -> BuildResult:
        summary = result.summary or ""
        summary = _strip_pii_from_text(summary)
        return result.model_copy(update={"summary": summary})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _combined_text(result: BuildResult) -> str:
    """Flatten all text fields into one string for pattern matching."""
    parts = [result.summary or ""]
    for c in result.components:
        parts.append(c.name)
        parts.append(c.brand)
        parts.extend(c.specs.values())
    return " ".join(parts)


def _is_allowlisted_url(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host in _AFFILIATE_ALLOWED_HOSTS


def _strip_pii_from_text(text: str) -> str:
    # Strip phone numbers
    text = _PHONE_PATTERN.sub("[removed]", text)
    # Strip email addresses
    text = _EMAIL_PATTERN.sub("[removed]", text)

    # Strip external URLs not in the affiliate allowlist
    def _maybe_strip_url(m: re.Match) -> str:  # noqa: E306
        url = m.group(0)
        return url if _is_allowlisted_url(url) else "[removed]"

    text = _URL_PATTERN.sub(_maybe_strip_url, text)
    return text


# Module-level singleton
output_guardrail = OutputGuardrail()
