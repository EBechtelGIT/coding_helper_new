"""Web search and fetch tools using DuckDuckGo and URL fetching."""

import re
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError
from html.parser import HTMLParser

from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None


class WebSearchSchema(BaseModel):
    query: str = Field(description="Search query")
    max_results: int = Field(default=5, description="Maximum number of results (default: 5)")


def web_search_func(query: str, max_results: int = 5) -> str:
    """Search the web using DuckDuckGo."""
    if DDGS is None:
        return "Error: duckduckgo-search is not installed. Run: pip install duckduckgo-search"

    try:
        max_results = int(max_results)
    except (ValueError, TypeError):
        max_results = 5

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))

        if not results:
            return f"No results found for query: {query}"

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.get('title', 'No title')}")
            lines.append(f"   URL: {r.get('href', 'No URL')}")
            lines.append(f"   {r.get('body', 'No description')}")
            lines.append("")
        return "\n".join(lines).strip()
    except Exception as e:
        return f"Error during web search: {e}"


class WebFetchSchema(BaseModel):
    url: str = Field(description="URL to fetch content from")
    max_length: int = Field(default=4000, description="Maximum characters to return (default: 4000)")


class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self._texts = []
        self._skip = False
        self._current = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True
        if tag in ("br", "p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div"):
            if self._current:
                self._texts.append("".join(self._current).strip())
                self._current = []

    def handle_endtag(self, tag):
        if tag in ("script", "style", "nav", "footer", "header"):
            self._skip = True
        if tag in ("br", "p", "h1", "h2", "h3", "h4", "h5", "h6", "li", "div"):
            if self._current:
                self._texts.append("".join(self._current).strip())
                self._current = []

    def handle_data(self, data):
        if not self._skip:
            self._current.append(data)

    def get_text(self):
        if self._current:
            self._texts.append("".join(self._current).strip())
        return "\n".join(t for t in self._texts if t)


def web_fetch_func(url: str, max_length: int = 4000) -> str:
    """Fetch and extract text content from a URL."""
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="ignore")
    except HTTPError as e:
        return f"Error: HTTP {e.code} - {e.reason}"
    except URLError as e:
        return f"Error: Could not fetch URL: {e.reason}"
    except Exception as e:
        return f"Error: {e}"

    extractor = _TextExtractor()
    extractor.feed(raw)
    text = extractor.get_text()

    text = re.sub(r"\n{3,}", "\n\n", text).strip()

    if len(text) > max_length:
        text = text[:max_length] + f"\n... (truncated, {len(text) - max_length} more chars)"

    return text


def get_web_tools() -> list[StructuredTool]:
    return [
        StructuredTool.from_function(
            func=web_search_func,
            name="web_search",
            description="Search the web using DuckDuckGo. Returns titles, URLs, and snippets.",
            args_schema=WebSearchSchema,
        ),
        StructuredTool.from_function(
            func=web_fetch_func,
            name="web_fetch",
            description="Fetch and extract readable text content from a URL. Use to read web pages, documentation, or API responses.",
            args_schema=WebFetchSchema,
        ),
    ]
