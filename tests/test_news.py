from pathlib import Path

from app.news import load_sample_articles


def test_load_sample_articles():
    articles = load_sample_articles(str(Path("data/sample_articles.json")))

    assert len(articles) >= 1
    assert articles[0].title
    assert articles[0].body
