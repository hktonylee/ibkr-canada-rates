"""HTTP utilities for downloading IBKR Canada pages."""
from __future__ import annotations

from typing import Optional
from urllib.request import Request, urlopen


def fetch_html(url: str, *, user_agent: Optional[str] = None, timeout: int = 30) -> str:
    """Download the HTML contents of ``url`` and return it as text."""
    headers = {}
    if user_agent is not None:
        headers["User-Agent"] = user_agent
    request = Request(url, headers=headers)
    with urlopen(request, timeout=timeout) as response:  # nosec: B310 - trusted URL
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")
