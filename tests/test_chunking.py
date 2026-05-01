from app.chunking import split_articles
from app.config import Settings
from app.models import Article


def test_split_articles_preserves_source_metadata():
    article = Article(
        id="a1",
        title="AI news",
        url="https://example.com/ai",
        source="Example News",
        published_at="2026-05-01T00:00:00Z",
        body="Sentence one. Sentence two. Sentence three.",
    )

    chunks = split_articles([article], Settings(OPENAI_API_KEY="test-key"))

    assert chunks
    assert chunks[0].article_id == "a1"
    assert chunks[0].title == "AI news"
    assert chunks[0].url == "https://example.com/ai"
    assert chunks[0].contextual_text == chunks[0].text
