from fastapi import Request
from slowapi import Limiter


def _get_client_ip(request: Request) -> str:
    """Rate-limit key: prefer X-Real-IP set by the reverse proxy over the raw
    client address. This prevents trivial bypass via a spoofed X-Forwarded-For
    header while still working correctly behind nginx.

    nginx must be configured to set and strip this header:
        proxy_set_header X-Real-IP $remote_addr;
    """
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if request.client:
        return request.client.host
    return "unknown"


limiter = Limiter(key_func=_get_client_ip)
