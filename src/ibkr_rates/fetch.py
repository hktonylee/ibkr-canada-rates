"""HTTP utilities for downloading IBKR Canada and US pages."""
from __future__ import annotations

from typing import Optional
from urllib.request import Request, urlopen


DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch_html(url: str, *, user_agent: Optional[str] = None, timeout: int = 30) -> str:
    """Download the HTML contents of ``url`` and return it as text."""
    headers = {"User-Agent": user_agent or DEFAULT_USER_AGENT}
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:  # nosec: B310 - trusted URL
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")
