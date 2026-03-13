"""Structured guardrail event logging.

Events are NOT persisted to the database.  They are emitted as JSON-formatted
WARNING log records to whatever log sink the process uses (stdout in Docker).

Log format example::

    {"timestamp": "2026-03-13T12:00:00Z", "ip": "1.2.3.4",
     "guardrail": "InputGuardrail.duplicate", "action": "blocked",
     "reason": "Duplicate request detected. Please wait before resubmitting."}
"""

import json
import logging
from datetime import UTC, datetime
from typing import Literal

_log = logging.getLogger("security.events")

Action = Literal["blocked", "warned", "stripped"]


def emit(
    *,
    ip: str,
    guardrail_name: str,
    action_taken: Action,
    reason: str,
) -> None:
    """Emit a structured JSON guardrail event at WARNING level."""
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "ip": ip,
        "guardrail": guardrail_name,
        "action": action_taken,
        "reason": reason,
    }
    _log.warning(json.dumps(event))
