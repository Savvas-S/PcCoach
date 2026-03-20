"""Minimal abuse / toxicity blocklist.

Keep this list short and focused.  It is intentionally NOT comprehensive —
the goal is to catch obvious abuse in the free-text fields, not to build a
full-spectrum content classifier.

Do NOT add borderline terms.  If a term produces false positives on
legitimate PC build requests, remove it.

MAINTENANCE: Patterns are compiled once at import time.  Restart the service
after editing this file (or implement hot-reload if needed in production).
"""

import re

# Each entry is a compiled regex pattern.
# Patterns are case-insensitive and matched anywhere in the combined text.
_RAW_PATTERNS: list[str] = [
    # Explicit violence / threats — require threatening context to avoid
    # false positives on gaming slang ("kill it in games", "bomb-proof build")
    r"\b(?:kill|murder|attack)\s+(?:you|him|her|them|people|someone|everyone)\b",
    r"\b(?:bomb\s+threat|terroris[mt])\b",
    # Extreme / crude sexual content triggers
    r"\b(?:porn|xxx|onlyfans|nude|naked)\b",
    r"\b(?:suck|lick|eat)\s+(?:my\s+)?(?:dick|cock|pussy|ass)\b",
    r"\b(?:blow\s*job|hand\s*job|jerk\s+off)\b",
    # Hate speech — only the most unambiguous slurs (keep this list very short)
    # We use Unicode-normalised regex-safe representations to avoid storing
    # slur strings literally in source.  These are the ASCII forms.
    r"\bn[i1!]gg[ae3]r\b",
    r"\bfagg[o0]t\b",
    r"\bc[u\*]nt\b",
    # Spam / self-promotion patterns that are clearly off-topic
    r"\bWhatsApp\s+\+?\d{7,}\b",
]

BLOCKLIST: list[re.Pattern[str]] = [re.compile(p, re.IGNORECASE) for p in _RAW_PATTERNS]
