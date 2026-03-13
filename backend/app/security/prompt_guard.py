"""Prompt injection defence for user-supplied text.

Sanitizes free-text fields before they are embedded in messages sent to
Claude.  The goal is not to block bad users at this layer (InputGuardrail
does that) but to neutralise injection payloads that slip through, so that
even a successful injection attempt produces unusable output.
"""

import logging
import re

_log = logging.getLogger("security.prompt_guard")

# Hard cap on any single user-supplied string field.
MAX_FIELD_LENGTH = 2_000

# ---------------------------------------------------------------------------
# Patterns that are characteristic of prompt-injection attacks.
# We log when these are detected but do NOT raise — blocking happens in the
# InputGuardrail layer.  Here we only strip / escape.
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # Instruction-override phrases
    (
        "ignore_previous",
        re.compile(r"ignore\s+(?:all\s+)?previous\s+instructions?", re.I),
    ),
    ("you_are_now", re.compile(r"you\s+are\s+now\b", re.I)),
    ("act_as", re.compile(r"\bact\s+as\b", re.I)),
    ("jailbreak", re.compile(r"\bjailbreak\b", re.I)),
    ("dan_mode", re.compile(r"\bDAN\b")),
    ("do_anything_now", re.compile(r"do\s+anything\s+now", re.I)),
    ("new_instructions", re.compile(r"new\s+instructions?\b", re.I)),
    ("disregard", re.compile(r"\bdisregard\b", re.I)),
    ("override", re.compile(r"\boverride\b", re.I)),
    (
        "system_prompt_leak",
        re.compile(
            r"(?:reveal|show|print|output|repeat)\s+(?:your\s+)?(?:system\s+)?prompt",
            re.I,
        ),
    ),
    ("role_change", re.compile(r"(?:pretend|imagine)\s+you\s+are\b", re.I)),
]

# XML-like tags used to inject structural context into Claude's prompt.
# We strip the angle brackets to defang them.
_XML_TAG_PATTERN = re.compile(
    r"<\s*/?\s*(?:system|prompt|instructions?|context|human|assistant|user)\s*(?:/\s*)?>",
    re.I,
)

# Triple-dashes and backtick fences are used to break out of delimiters.
_STRUCTURAL_CHARS = re.compile(r"`{3,}|-{3,}")


def sanitize_user_input(text: str) -> str:
    """Return a sanitised copy of *text* safe to embed in a Claude message.

    Operations performed (in order):
    1. Truncate to MAX_FIELD_LENGTH characters.
    2. Log (not raise) if any injection pattern is detected.
    3. Strip defanged XML tags.
    4. Neutralise code-fence and triple-dash structural characters.
    5. Strip leading/trailing whitespace.
    """
    if not text:
        return text

    # 1. Truncate
    if len(text) > MAX_FIELD_LENGTH:
        _log.warning(
            "prompt_guard: input truncated from %d to %d chars",
            len(text),
            MAX_FIELD_LENGTH,
        )
        text = text[:MAX_FIELD_LENGTH]

    # 2. Detect and log injection patterns (do NOT raise here)
    for name, pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            _log.warning(
                "prompt_guard: suspicious pattern detected pattern=%s",
                name,
            )

    # 3. Strip defanged XML control tags
    text = _XML_TAG_PATTERN.sub("", text)

    # 4. Neutralise structural characters (replace backtick-fences / triple-dashes)
    text = _STRUCTURAL_CHARS.sub(" ", text)

    # 5. Strip whitespace
    return text.strip()
