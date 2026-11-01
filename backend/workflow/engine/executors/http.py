"""
AutoFlow AI X — HTTP Executor
================================
Makes outbound HTTP requests with rigorous Server-Side Request Forgery (SSRF)
containment and response limits.
"""

import ipaddress
import json
import logging
import os
import socket
from urllib.parse import urlsplit
from typing import Any

import httpx

from backend.workflow.dsl.schema import WorkflowNodeDSL
from backend.workflow.engine.context import ExecutionContext
from backend.workflow.engine.executors.base import BaseExecutor, ExecutorResult

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30  # seconds
MAX_TIMEOUT = 60      # seconds
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB cap to prevent denial-of-service via memory exhaustion

FORBIDDEN_METADATA_HOSTS = {
    "metadata.google.internal",
    "169.254.169.254",
    "fd00:ec2::254",
    "instance-data",
}

BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),          # Broadcast/unspecified host
    ipaddress.ip_network("10.0.0.0/8"),         # Private RFC 1918
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),        # IPv4 Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local (RFC 3927) & Cloud Metadata
    ipaddress.ip_network("172.16.0.0/12"),      # Private RFC 1918
    ipaddress.ip_network("192.0.0.0/24"),       # IETF Protocol Assignments
    ipaddress.ip_network("192.0.2.0/24"),       # Documentation TEST-NET-1
    ipaddress.ip_network("192.88.99.0/24"),     # 6to4 Relay Anycast
    ipaddress.ip_network("192.168.0.0/16"),     # Private RFC 1918
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("198.51.100.0/24"),    # Documentation TEST-NET-2
    ipaddress.ip_network("203.0.113.0/24"),     # Documentation TEST-NET-3
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Limited Broadcast
    # IPv6 ranges
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("::1/128"),            # IPv6 Loopback
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6
    ipaddress.ip_network("100::/64"),           # Discard-Only
    ipaddress.ip_network("2001:db8::/32"),      # Documentation
    ipaddress.ip_network("fc00::/7"),           # Unique Local (RFC 4193)
    ipaddress.ip_network("fe80::/10"),          # Link-Local
    ipaddress.ip_network("ff00::/8"),           # Multicast
]

DANGEROUS_FORWARD_HEADERS = {
    "host",
    "x-forwarded-for",
    "x-forwarded-host",
    "x-real-ip",
}


def is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address is in a loopback, private, link-local, or reserved network."""
    if (
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
        or ip.is_unspecified
    ):
        return True
    for net in BLOCKED_IP_NETWORKS:
        if ip in net:
            return True
    return False


def validate_url_for_ssrf(url: str, allow_insecure_http: bool = False) -> tuple[str, list[str]]:
    """
    Validate target URL against SSRF attacks:
      - Enforces HTTPS scheme (HTTP only allowed when allow_insecure_http=True)
      - Resolves DNS hostname and checks every resolved IP address
      - Blocks private, loopback, link-local, and cloud metadata addresses
    Returns (hostname, resolved_ips).
    Raises ValueError on SSRF detection.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    parsed = urlsplit(url)
    if not parsed.scheme:
        raise ValueError("Missing URL scheme (e.g. 'https://').")

    scheme = parsed.scheme.lower()
    allowed_schemes = ("https", "http") if allow_insecure_http else ("https",)
    if scheme not in allowed_schemes:
        raise ValueError(
            f"Scheme '{scheme}' is prohibited. Only HTTPS requests are allowed for workflow HTTP nodes."
        )

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Target URL does not contain a valid hostname.")

    clean_hostname = hostname.strip().lower()
    if clean_hostname in FORBIDDEN_METADATA_HOSTS:
        raise ValueError(f"Access to cloud metadata destination '{clean_hostname}' is strictly prohibited.")

    # Check if hostname itself is directly an IP literal
    try:
        direct_ip = ipaddress.ip_address(clean_hostname)
        if is_ip_blocked(direct_ip):
            raise ValueError(
                f"Destination IP '{direct_ip}' belongs to a private/loopback/metadata network and is blocked."
            )
        return clean_hostname, [str(direct_ip)]
    except ValueError as e:
        if "belongs to a private/loopback" in str(e):
            raise

    # Resolve hostname via DNS
    port = parsed.port or (443 if scheme == "https" else 80)
    try:
        addr_info = socket.getaddrinfo(clean_hostname, port, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise ValueError(f"DNS resolution failed for hostname '{clean_hostname}': {e}")

    resolved_ips = []
    for entry in addr_info:
        ip_str = entry[4][0]
        resolved_ips.append(ip_str)
        try:
            ip_obj = ipaddress.ip_address(ip_str)
            if is_ip_blocked(ip_obj):
                raise ValueError(
                    f"Destination '{clean_hostname}' resolved to prohibited IP '{ip_str}' (loopback, private, or metadata network)."
                )
        except ValueError as e:
            if "prohibited IP" in str(e):
                raise

    if not resolved_ips:
        raise ValueError(f"No IP addresses could be resolved for '{clean_hostname}'.")

    return clean_hostname, resolved_ips


class HttpRequestExecutor(BaseExecutor):
    """
    Makes an outbound HTTP request with SSRF protection, size limits, and bounded timeouts.

    Required params:
        url    : Target URL (HTTPS only unless ALLOW_INSECURE_HTTP is enabled)
        method : HTTP method (GET, POST, PUT, PATCH, DELETE)

    Optional params:
        headers : dict of request headers
        body    : request body (dict -> JSON, string -> raw)
        params  : URL query parameters
        timeout : request timeout in seconds (default 30, max 60)
    """

    async def execute(
        self,
        node: WorkflowNodeDSL,
        context: ExecutionContext,
        resolved_params: dict[str, Any],
    ) -> ExecutorResult:
        url = resolved_params.get("url", "")
        method = resolved_params.get("method", "POST").upper()
        headers = dict(resolved_params.get("headers", {}) or {})
        body = resolved_params.get("body")
        query_params = resolved_params.get("params", {})
        timeout_param = resolved_params.get("timeout", DEFAULT_TIMEOUT)

        try:
            timeout = max(1, min(int(timeout_param), MAX_TIMEOUT))
        except (ValueError, TypeError):
            timeout = DEFAULT_TIMEOUT

        if not url:
            return ExecutorResult.fail("'url' is required for http_request.")

        # 1. SSRF Pre-flight validation
        allow_insecure = os.getenv("ALLOW_INSECURE_HTTP", "false").lower() in ("true", "1")
        try:
            validate_url_for_ssrf(url, allow_insecure_http=allow_insecure)
        except ValueError as e:
            logger.warning(f"[HTTP] Blocked SSRF attempt: {e} (URL: {url})")
            return ExecutorResult.fail(f"SSRF Protection blocked request: {e}")

        # 2. Header sanitization: strip spoofed internal routing headers
        sanitized_headers = {
            k: v for k, v in headers.items()
            if k.lower() not in DANGEROUS_FORWARD_HEADERS
        }

        logger.info(f"[HTTP] {method} {url}")

        # 3. Execute request with disabled redirects (redirects re-check SSRF boundary)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            try:
                kwargs: dict[str, Any] = {
                    "headers": sanitized_headers,
                    "params": query_params,
                }
                if body is not None:
                    if isinstance(body, dict):
                        kwargs["json"] = body
                    else:
                        kwargs["content"] = str(body)

                async with client.stream(method, url, **kwargs) as response:
                    # Guard against redirect-based SSRF
                    if response.is_redirect:
                        location = response.headers.get("location", "")
                        logger.warning(f"[HTTP] Denied redirect from {url} to {location}")
                        return ExecutorResult.fail(
                            f"HTTP Redirects are disabled for security containment (target redirected to: {location})"
                        )

                    # Stream response with maximum payload size cap
                    content_chunks: list[bytes] = []
                    total_bytes = 0
                    async for chunk in response.aiter_bytes():
                        total_bytes += len(chunk)
                        if total_bytes > MAX_RESPONSE_BYTES:
                            return ExecutorResult.fail(
                                f"Response size exceeded safety limit of {MAX_RESPONSE_BYTES} bytes."
                            )
                        content_chunks.append(chunk)

                    raw_body = b"".join(content_chunks).decode("utf-8", errors="replace")
                    status_code = response.status_code

                if status_code >= 400:
                    msg = f"HTTP {status_code} from {url}: {raw_body[:300]}"
                    logger.warning(f"[HTTP] {msg}")
                    return ExecutorResult.fail(msg, output={"status_code": status_code})

                # Parse JSON if possible
                try:
                    response_data = json.loads(raw_body)
                except Exception:
                    response_data = raw_body

                logger.info(f"[HTTP] {method} {url} -> {status_code}")

                return ExecutorResult.ok(
                    output={
                        "status_code": status_code,
                        "response": response_data,
                        "url": url,
                        "bytes": total_bytes,
                    }
                )

            except httpx.HTTPStatusError as e:
                msg = f"HTTP {e.response.status_code} from {url}: {e.response.text[:300]}"
                logger.warning(f"[HTTP] {msg}")
                return ExecutorResult.fail(msg, output={"status_code": e.response.status_code})

            except httpx.RequestError as e:
                msg = f"Request error for {url}: {e}"
                logger.error(f"[HTTP] {msg}")
                return ExecutorResult.fail(msg)
