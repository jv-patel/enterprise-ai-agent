"""
Web search tool.

Uses the Brave Search API (api.search.brave.com), keyed by WEB_SEARCH_API_KEY.
Returns a compact list of {title, url, snippet} results for the model to
reason over and cite.
"""
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.agents.tools.registry import ToolSpec
from app.config import get_settings
from app.core.cache import cached
from app.core.exceptions import ExternalServiceError
from app.core.logging_config import get_logger

logger = get_logger(__name__)

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=6), reraise=True)
async def _search(query: str, count: int) -> dict:
    settings = get_settings()
    if not settings.WEB_SEARCH_API_KEY:
        raise ExternalServiceError(
            "Web search is not configured. Set WEB_SEARCH_API_KEY.",
            error_code="web_search_not_configured",
        )

    headers = {"Accept": "application/json", "X-Subscription-Token": settings.WEB_SEARCH_API_KEY}
    params = {"q": query, "count": count}

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(BRAVE_SEARCH_URL, headers=headers, params=params)
    if response.status_code >= 400:
        logger.error("Web search failed %s: %s", response.status_code, response.text)
        raise ExternalServiceError(f"Web search failed with status {response.status_code}", error_code="web_search_error")
    return response.json()


@cached(600, key_prefix="web_search")
async def _web_search(query: str, count: int = 5) -> dict:
    data = await _search(query, min(max(count, 1), 10))
    results = []
    for item in data.get("web", {}).get("results", [])[:count]:
        results.append(
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("description"),
            }
        )
    return {"query": query, "results": results}


def build_web_search_tool() -> ToolSpec:
    return ToolSpec(
        name="web_search",
        description="Search the live web for current information not in the model's training data.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search query."},
                "count": {"type": "integer", "description": "Number of results to return (1-10). Defaults to 5."},
            },
            "required": ["query"],
        },
        handler=_web_search,
    )
