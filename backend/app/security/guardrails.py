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
import json
import logging
import re
import unicodedata
from dataclasses import dataclass

from cachetools import TTLCache

from app.models.builder import BudgetRange, BuildRequest, ComponentSearchRequest
from app.security.blocklist import BLOCKLIST

# ---------------------------------------------------------------------------
# Text normalization for blocklist matching
# ---------------------------------------------------------------------------
# Zero-width and invisible Unicode characters used to break regex matching.
_INVISIBLE_CHARS = re.compile(
    r"[\u200b\u200c\u200d\u200e\u200f\ufeff\u00ad\u034f"
    r"\u2060\u2061\u2062\u2063\u2064\u206a-\u206f]"
)
# Leetspeak substitutions — only digits commonly used as letter replacements.
# Applied contextually (only when a digit sits between letters) to avoid
# corrupting legitimate numbers like "32GB" or "RTX 5070".
_LEET_DIGIT_MAP = {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}
_LEET_SYMBOL_MAP = str.maketrans("@$!", "as!")
# Matches a digit that has a letter on at least one side (e.g. "d1ck", "pr0n")
_LEET_DIGIT_RE = re.compile(r"(?<=[a-z])(\d)(?=[a-z])|(?<=[a-z])(\d)$|^(\d)(?=[a-z])")
# Common Cyrillic → Latin homoglyphs (NFKD doesn't cover these)
_HOMOGLYPHS: dict[str, str] = {
    "\u0430": "a",
    "\u0435": "e",
    "\u043e": "o",
    "\u0440": "p",
    "\u0441": "c",
    "\u0443": "y",
    "\u0445": "x",
    "\u043a": "k",
    "\u0456": "i",
    "\u0458": "j",
    "\u04bb": "h",
    "\u0455": "s",
}


# Spaceless patterns — matched against text with ALL spaces removed to catch
# "s u c k  d i c k" style bypasses. These use substring matching (no \b)
# since word boundaries don't exist in collapsed text.
_SPACELESS_BLOCKLIST: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"suck(?:my)?dick",
        r"suck(?:my)?cock",
        r"(?:lick|eat)(?:my)?(?:dick|cock|pussy|ass)",
        r"blowjob",
        r"handjob",
        r"jerkoff",
    ]
]


def _normalize_for_blocklist(text: str) -> str:
    """Normalize text to defeat common blocklist bypass techniques.

    Applied before regex matching, not to the stored/displayed text.
    """
    # 1. Unicode NFKD normalization
    text = unicodedata.normalize("NFKD", text)
    # 2. Strip invisible/zero-width characters
    text = _INVISIBLE_CHARS.sub("", text)
    # 3. Cyrillic homoglyph substitution
    text = "".join(_HOMOGLYPHS.get(c, c) for c in text)
    # 4. Strip non-ASCII (catches remaining exotic bypasses)
    text = text.encode("ascii", "ignore").decode("ascii")

    # 5. Leetspeak: substitute digits only when adjacent to letters
    #    ("d1ck" → "dick" but "32GB" stays "32GB")
    def _leet_replace(m: re.Match) -> str:
        d = m.group(1) or m.group(2) or m.group(3)
        return _LEET_DIGIT_MAP.get(d, d)

    text = _LEET_DIGIT_RE.sub(_leet_replace, text)
    text = text.translate(_LEET_SYMBOL_MAP)
    return text


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

    def check_build_content(
        self,
        *,
        notes: str | None,
        budget_range: BudgetRange,
    ) -> GuardrailResult:
        """Content-only checks (blocklist, budget) without duplicate detection.

        Use this for all requests — cache hits included. Duplicate detection
        is handled separately by check_build_duplicate().
        """
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

        return _ALLOWED

    def check_build_duplicate(
        self,
        *,
        client_ip: str,
        body_hash: str,
    ) -> GuardrailResult:
        """Duplicate detection only for POST /api/v1/build.

        Content checks are handled separately by check_build_content()
        which runs earlier in the request pipeline (before the cache check).
        """
        return self._check_duplicate(client_ip, body_hash)

    def check_search_duplicate(
        self,
        *,
        client_ip: str,
        body_hash: str,
    ) -> GuardrailResult:
        """Duplicate detection only for POST /api/v1/search.

        Content checks (blocklist) are handled separately by
        check_search_content() which runs earlier in the request pipeline
        (before the cache check). This method only adds duplicate detection
        for uncached requests that will hit Claude.
        """
        return self._check_duplicate(client_ip, body_hash)

    def check_search_content(self, *, description: str) -> GuardrailResult:
        """Content-only checks (blocklist) without duplicate detection.

        Use this for requests that will be served from cache — the blocklist
        must still run, but duplicate counting should be skipped.
        """
        return self._check_blocklist(description.lower())

    # ------------------------------------------------------------------
    # Individual checks
    # ------------------------------------------------------------------

    def _check_hardware_intent(
        self, combined_text: str, budget_range: BudgetRange
    ) -> GuardrailResult:
        """Reject requests with no discernible PC/hardware intent.

        The `goal` and `budget_range` enum fields already encode hardware
        intent — every valid UserGoal is a hardware use-case by definition.
        We therefore only flag requests that have NO notes at all AND whose
        notes are purely numeric/empty (a degenerate edge case).

        We do NOT gate on hardware keywords in notes: users write things like
        "make it quiet" or "for my son's birthday" which are perfectly valid
        build constraints that don't mention hardware terms.
        """
        # All intent is expressed through validated enum fields; notes are
        # optional context.  Any request that passed Pydantic validation has
        # a valid goal and budget — that is sufficient proof of intent.
        return _ALLOWED

    def _check_blocklist(self, combined_text: str) -> GuardrailResult:
        """Reject requests matching the abuse blocklist.

        Normalizes text before matching to defeat zero-width characters,
        leetspeak, homoglyphs, and character-spacing bypass techniques.
        Checks both with and without spaces to catch "s u c k" patterns.
        """
        normalized = _normalize_for_blocklist(combined_text)
        # Check normalized text with standard patterns
        for pattern in BLOCKLIST:
            if pattern.search(normalized):
                _log.warning(
                    "input_guardrail: blocklist match pattern=%s",
                    pattern.pattern[:30],
                )
                return GuardrailResult(
                    allowed=False,
                    reason="Request contains disallowed content.",
                )
        # Also check with spaces collapsed to catch "s u c k  d i c k"
        spaceless = normalized.replace(" ", "")
        for pattern in _SPACELESS_BLOCKLIST:
            if pattern.search(spaceless):
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
        """Sanity-check the numeric range implied by the budget enum.

        All valid BudgetRange values have upper bounds ≤ _BUDGET_MAX, so this
        check never fires for enum-validated inputs (Pydantic enforces the enum
        before we reach here).  It exists as a defence-in-depth guard against
        future budget tiers being added with values outside the expected range.
        """
        _lower, upper = _BUDGET_NUMERIC.get(budget_range, (0.0, 0.0))
        if upper > _BUDGET_MAX:
            _log.warning(
                "input_guardrail: budget out of range budget=%s upper=%s",
                budget_range.value,
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


def hash_build_request(payload: BuildRequest) -> str:
    """Return a stable SHA-256 hex digest of a BuildRequest.

    Uses a canonical JSON form (sorted keys, no whitespace) derived from the
    parsed Pydantic model rather than the raw request bytes. This ensures that
    two requests with identical field values always produce the same hash,
    regardless of key ordering or whitespace differences in the original JSON.

    Notes are case-insensitive: "Best CPU" and "best cpu" produce the same hash.
    """
    data = payload.model_dump(mode="json")
    # Normalize trivial notes to None for better cache hits
    notes = data.get("notes")
    if isinstance(notes, str):
        normalized = notes.strip().lower()
        if normalized in {"", "none", "n/a", "nothing", "-", "."}:
            data["notes"] = None
        else:
            data["notes"] = normalized
    # Sort existing_parts for order-independent hashing
    if data.get("existing_parts"):
        data["existing_parts"] = sorted(data["existing_parts"])
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def hash_search_request(payload: ComponentSearchRequest) -> str:
    """Return a stable SHA-256 hex digest of a ComponentSearchRequest."""
    data = payload.model_dump(mode="json")
    if isinstance(data.get("description"), str):
        data["description"] = data["description"].lower()
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


# Module-level singleton — share the duplicate cache across all requests.
input_guardrail = InputGuardrail()
