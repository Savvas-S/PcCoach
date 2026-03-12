import ipaddress

from fastapi import Request
from slowapi import Limiter


def _is_trusted_proxy(host: str) -> bool:
    """Return True if the direct client is a loopback or RFC-1918 private address.

    Only connections from a private/loopback address can be trusted to set X-Real-IP,
    since those come from a reverse proxy (nginx) running on the same host or network.
    """
    try:
        addr = ipaddress.ip_address(host)
        return addr.is_loopback or addr.is_private
    except ValueError:
        return False


def _get_client_ip(request: Request) -> str:
    """Rate-limit key: trust X-Real-IP only when the direct connection comes from
    a loopback or private address (i.e., the nginx reverse proxy). This prevents a
    public client from injecting a spoofed X-Real-IP header to bypass rate limits.

    nginx must be configured to set (and not forward) this header:
        proxy_set_header X-Real-IP $remote_addr;
    """
    raw = request.client.host if request.client else None
    if raw and _is_trusted_proxy(raw):
        real_ip = request.headers.get("X-Real-IP", "").strip()
        if real_ip:
            try:
                ipaddress.ip_address(real_ip)  # reject malformed values
                return real_ip
            except ValueError:
                pass
    return raw or "unknown"


limiter = Limiter(key_func=_get_client_ip)
