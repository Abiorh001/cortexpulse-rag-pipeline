from hashlib import sha256
from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import Settings
from app.models import Article, ArticleChunk


def split_articles(articles: list[Article], settings: Settings) -> list[ArticleChunk]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", "? ", "! ", " ", ""],
    )

    chunks: list[ArticleChunk] = []
    for article in articles:
        for index, raw_text in enumerate(splitter.split_text(article.body)):
            text = clean_chunk_text(raw_text)
            if not text:
                continue
            chunk_id = stable_chunk_id(article.id, index, text)
            chunks.append(
                ArticleChunk(
                    id=chunk_id,
                    article_id=article.id,
                    title=article.title,
                    url=article.url,
                    source=article.source,
                    published_at=article.published_at,
                    chunk_index=index,
                    text=text,
                    contextual_text=text,
                )
            )
    return chunks


def stable_chunk_id(article_id: str, index: int, text: str) -> str:
    digest = sha256(f"{article_id}:{index}:{text}".encode("utf-8")).hexdigest()
    return str(uuid5(NAMESPACE_URL, digest))


def clean_chunk_text(text: str) -> str:
    return text.strip().lstrip(".;:- ").strip()
