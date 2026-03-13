"""Input guardrails for the POST /api/v1/build endpoint.

All checks run BEFORE the request reaches Claude.  Every check returns a
``GuardrailResult``; the first failing check short-circuits the pipeline.

Logging contract
----------------
- Events are logged at WARNING via the ``security.guardrails`` logger.
- We never log the offending user text — only metadata (rule name, IP,
  action taken).

Threading / concurrency
-----------------------
The in-memory TTLCache used for duplicate detection is NOT thread-safe for
concurrent writes.  CPython's GIL protects individual dict operations, which
is sufficient for a single-process asyncio server.  Replace with Redis for
multi-process / multi-node deployments.
"""

import hashlib
import logging
from dataclasses import dataclass

from cachetools import TTLCache

from app.models.builder import BudgetRange
from app.security.blocklist import BLOCKLIST

_log = logging.getLogger("security.guardrails")

# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GuardrailResult:
    allowed: bool
    reason: str


_ALLOWED = GuardrailResult(allowed=True, reason="ok")


# ---------------------------------------------------------------------------
# Keyword allowlist — at least one token must appear in the combined input.
# ---------------------------------------------------------------------------
_HARDWARE_KEYWORDS: frozenset[str] = frozenset(
    {
        "pc",
        "computer",
        "build",
        "cpu",
        "gpu",
        "ram",
        "gaming",
        "workstation",
        "render",
        "edit",
        "stream",
        "budget",
        "performance",
        "upgrade",
        "processor",
        "motherboard",
        "storage",
        "ssd",
        "monitor",
        "keyboard",
        "mouse",
        "case",
        "psu",
        "power supply",
        "cooling",
        "fan",
        "thermal",
    }
)


# ---------------------------------------------------------------------------
# Budget range → numeric (lower, upper) bounds used for sanity checks.
# "over_3000" upper bound is capped at 100_000 to reuse the same check.
# ---------------------------------------------------------------------------
_BUDGET_NUMERIC: dict[BudgetRange, tuple[float, float]] = {
    BudgetRange.range_0_1000: (0.0, 1_000.0),
    BudgetRange.range_1000_1500: (1_000.0, 1_500.0),
    BudgetRange.range_1500_2000: (1_500.0, 2_000.0),
    BudgetRange.range_2000_3000: (2_000.0, 3_000.0),
    BudgetRange.over_3000: (3_000.0, 100_000.0),
}

_BUDGET_MIN = 50.0
_BUDGET_MAX = 100_000.0


# ---------------------------------------------------------------------------
# Duplicate-request cache  (per-IP hash → hit count)
# 600-second TTL, 10-minute sliding window, max 50 k unique entries.
# ---------------------------------------------------------------------------
_DUP_WINDOW = 600  # seconds
_DUP_MAX = 3  # hits before 429
# The TTLCache key is (ip, body_hash); value is request count.
_dup_cache: TTLCache = TTLCache(maxsize=50_000, ttl=_DUP_WINDOW)


class InputGuardrail:
    """Stateless (except for the shared duplicate cache) input validator."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def check(
        self,
        *,
        notes: str | None,
        budget_range: BudgetRange,
        client_ip: str,
        body_hash: str,
        # Goal / other enum fields are always valid (Pydantic enforced).
    ) -> GuardrailResult:
        """Run all checks in priority order.  Returns on first failure."""
        combined_text = (notes or "").lower()

        result = self._check_hardware_intent(combined_text, budget_range)
        if not result.allowed:
            return result

        result = self._check_blocklist(combined_text)
        if not result.allowed:
            return result

        result = self._check_budget(budget_range)
        if not result.allowed:
            return result

        result = self._check_duplicate(client_ip, body_hash)
        if not result.allowed:
            return result

        return _ALLOWED

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_hardware_intent(
        self, combined_text: str, budget_range: BudgetRange
    ) -> GuardrailResult:
        """Reject requests with no discernible PC/hardware intent.

        Structured fields (goal, budget_range) already encode hardware intent
        — a request that specifies a valid UserGoal has clear intent by
        definition.  We check notes only to catch clearly off-topic text.
        If there is no notes text, intent is implied by the enum fields.
        """
        # If no free-text notes, intent is implied by the enum fields.
        if not combined_text:
            return _ALLOWED

        # If notes contain at least one hardware keyword, intent is clear.
        text_tokens = set(combined_text.split())
        # Also check multi-word keywords.
        for kw in _HARDWARE_KEYWORDS:
            if " " in kw:
                if kw in combined_text:
                    return _ALLOWED
            elif kw in text_tokens:
                return _ALLOWED

        # Notes exist but contain zero hardware keywords — likely off-topic
        # or spam text appended to a valid-looking request.
        _log.warning(
            "input_guardrail: no hardware intent detected "
            "budget=%s notes_len=%d",
            budget_range.value,
            len(combined_text),
        )
        return GuardrailResult(
            allowed=False,
            reason="Please describe your PC build goal and budget.",
        )

    def _check_blocklist(self, combined_text: str) -> GuardrailResult:
        """Reject requests matching the abuse blocklist."""
        for pattern in BLOCKLIST:
            if pattern.search(combined_text):
                _log.warning(
                    "input_guardrail: blocklist match pattern=%s",
                    pattern.pattern[:30],  # log only pattern prefix, not user text
                )
                return GuardrailResult(
                    allowed=False,
                    reason="Request contains disallowed content.",
                )
        return _ALLOWED

    def _check_budget(self, budget_range: BudgetRange) -> GuardrailResult:
        """Sanity-check the numeric range implied by the budget enum."""
        lower, upper = _BUDGET_NUMERIC.get(budget_range, (0.0, 0.0))
        if lower < _BUDGET_MIN or upper > _BUDGET_MAX:
            _log.warning(
                "input_guardrail: budget out of range budget=%s lower=%s upper=%s",
                budget_range.value,
                lower,
                upper,
            )
            return GuardrailResult(
                allowed=False,
                reason="Budget must be between \u20ac50 and \u20ac100,000.",
            )
        return _ALLOWED

    def _check_duplicate(self, client_ip: str, body_hash: str) -> GuardrailResult:
        """Rate-limit identical request bodies from the same IP.

        Allows up to _DUP_MAX identical requests within _DUP_WINDOW seconds.
        """
        key = f"{client_ip}:{body_hash}"
        count = _dup_cache.get(key, 0) + 1
        _dup_cache[key] = count
        if count > _DUP_MAX:
            _log.warning(
                "input_guardrail: duplicate request ip=%s count=%d",
                client_ip,
                count,
            )
            return GuardrailResult(
                allowed=False,
                reason="Duplicate request detected. Please wait before resubmitting.",
            )
        return _ALLOWED


def hash_request_body(body: bytes) -> str:
    """Return a compact SHA-256 hex digest of a raw request body."""
    return hashlib.sha256(body).hexdigest()


# Module-level singleton — share the duplicate cache across all requests.
input_guardrail = InputGuardrail()
