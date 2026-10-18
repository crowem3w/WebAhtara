"""Fetch a business website for ownership verification without letting callers reach internal hosts (SSRF guard)."""
from __future__ import annotations

import asyncio
import ipaddress
import socket
from urllib.parse import urljoin, urlparse

import httpx

MAX_BYTES = 500_000
MAX_REDIRECTS = 3
USER_AGENT = "AhtaraVerifier/1.0 (+https://ahtara.social)"


class UnsafeURL(Exception):
    pass


async def assert_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise UnsafeURL("Only http(s) URLs are allowed")
    loop = asyncio.get_running_loop()
    try:
        infos = await loop.getaddrinfo(parsed.hostname, parsed.port or (443 if parsed.scheme == "https" else 80), type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise UnsafeURL("Host does not resolve") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast or ip.is_unspecified:
            raise UnsafeURL("Host resolves to a non-public address")


async def fetch_public_html(url: str, timeout: float = 8.0) -> str:
    """GET `url`, following at most MAX_REDIRECTS redirects and re-checking every hop. Returns up to MAX_BYTES of text."""
    async with httpx.AsyncClient(follow_redirects=False, timeout=timeout, headers={"User-Agent": USER_AGENT}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            await assert_public_host(url)
            async with client.stream("GET", url) as resp:
                if resp.is_redirect:
                    url = urljoin(url, resp.headers.get("location", ""))
                    continue
                resp.raise_for_status()
                chunks, size = [], 0
                async for chunk in resp.aiter_bytes():
                    chunks.append(chunk)
                    size += len(chunk)
                    if size >= MAX_BYTES:
                        break
                return b"".join(chunks)[:MAX_BYTES].decode(resp.encoding or "utf-8", errors="replace")
    raise UnsafeURL("Too many redirects")
