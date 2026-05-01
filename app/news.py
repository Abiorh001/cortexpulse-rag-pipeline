import json
from pathlib import Path

import httpx

from app.config import Settings
from app.models import Article
from app.reliability import CircuitBreaker, retry_with_backoff


class NewsIngestionError(RuntimeError):
    """Raised when the live news source cannot produce usable articles."""


async def load_articles(settings: Settings) -> tuple[str, list[Article]]:
    try:
        articles = await fetch_guardian_articles(settings)
        if articles:
            return "guardian", articles
    except NewsIngestionError:
        pass

    return "sample", load_sample_articles(settings.sample_articles_path)


async def fetch_guardian_articles(settings: Settings) -> list[Article]:
    if not settings.guardian_api_key:
        raise NewsIngestionError("GUARDIAN_API_KEY is not configured")

    params = {
        "api-key": settings.guardian_api_key,
        "q": settings.guardian_query,
        "show-fields": "bodyText,headline,trailText",
        "order-by": "newest",
        "page-size": settings.max_articles,
        "type": "article",
    }

    breaker = CircuitBreaker(
        name="guardian",
        failure_threshold=settings.circuit_breaker_failure_threshold,
        reset_seconds=settings.circuit_breaker_reset_seconds,
    )

    async def request_guardian() -> dict:
        async with httpx.AsyncClient(timeout=settings.request_timeout_seconds) as client:
            response = await client.get(
                "https://content.guardianapis.com/search", params=params
            )
            response.raise_for_status()
            return response.json()

    try:
        payload = await retry_with_backoff(
            request_guardian,
            attempts=settings.retry_attempts,
            initial_backoff_seconds=settings.retry_initial_backoff_seconds,
            backoff_multiplier=settings.retry_backoff_multiplier,
            circuit_breaker=breaker,
        )
    except (httpx.HTTPError, ValueError, RuntimeError) as exc:
        raise NewsIngestionError(f"Guardian request failed: {exc}") from exc

    results = payload.get("response", {}).get("results", [])
    articles: list[Article] = []
    for item in results:
        fields = item.get("fields") or {}
        body = (fields.get("bodyText") or fields.get("trailText") or "").strip()
        title = fields.get("headline") or item.get("webTitle") or "Untitled"
        url = item.get("webUrl") or ""
        if not is_usable_article(title, url, body):
            continue
        articles.append(
            Article(
                id=item.get("id") or item.get("webUrl") or fields.get("headline", ""),
                title=title,
                url=url,
                source="The Guardian",
                published_at=item.get("webPublicationDate"),
                body=body,
            )
        )

    if not articles:
        raise NewsIngestionError("Guardian returned no articles with usable body text")
    return articles


def load_sample_articles(path: str) -> list[Article]:
    sample_path = Path(path)
    with sample_path.open("r", encoding="utf-8") as file:
        raw_articles = json.load(file)
    return [Article.model_validate(item) for item in raw_articles]


def is_usable_article(title: str, url: str, body: str) -> bool:
    text = body.strip()
    lowered_title = title.lower()
    lowered_url = url.lower()
    if len(text) < 600:
        return False
    if "/live/" in lowered_url or "live/" in lowered_url:
        return False
    if "as it happened" in lowered_title or "live updates" in lowered_title:
        return False
    if text.lower() in {"more coming up.", "more coming up"}:
        return False
    return True
