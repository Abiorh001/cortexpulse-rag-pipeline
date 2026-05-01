from collections import defaultdict
import asyncio

from app.chunking import split_articles
from app.config import Settings
from app.llm import OpenAIService
from app.models import Article, ArticleChunk, ChatResponse, IngestResponse
from app.news import load_articles
from app.vector_store import QdrantStore


class CortexPulsePipeline:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm = OpenAIService(settings)
        self.store = QdrantStore(settings)

    async def ingest(self) -> IngestResponse:
        source, articles = await load_articles(self.settings)
        chunks = split_articles(articles, self.settings)
        contextualized_chunks = chunks
        if self.settings.contextualization_enabled:
            contextualized_chunks = await self._contextualize_chunks(articles, chunks)
        texts_to_embed = [
            f"{chunk.contextual_text}\n\n{chunk.text}" for chunk in contextualized_chunks
        ]
        embeddings = await self.llm.embed_texts(texts_to_embed)
        indexed = await self.store.upsert_chunks(
            contextualized_chunks,
            embeddings,
            reset=True,
        )
        return IngestResponse(
            source=source,
            articles_loaded=len(articles),
            chunks_indexed=indexed,
            message=f"Indexed {indexed} chunks from {len(articles)} article(s).",
        )

    async def chat(self, question: str) -> ChatResponse:
        query_embedding = (await self.llm.embed_texts([question]))[0]
        chunks, citations = await self.store.search(
            query_embedding,
            limit=self.settings.retrieval_top_k,
        )
        answer = await self.llm.answer_question(question, chunks, citations)
        return ChatResponse(answer=answer, citations=citations)

    async def _contextualize_chunks(
        self, articles: list[Article], chunks: list[ArticleChunk]
    ) -> list[ArticleChunk]:
        article_by_id = {article.id: article for article in articles}
        grouped: dict[str, list[ArticleChunk]] = defaultdict(list)
        for chunk in chunks:
            grouped[chunk.article_id].append(chunk)

        contextualized: list[ArticleChunk] = []
        semaphore = asyncio.Semaphore(self.settings.contextualization_concurrency)

        async def contextualize_one(article: Article, chunk: ArticleChunk) -> ArticleChunk:
            async with semaphore:
                context = await self.llm.contextualize_chunk(article, chunk.text)
            return chunk.model_copy(update={"contextual_text": context})

        tasks = []
        for article_id, article_chunks in grouped.items():
            article = article_by_id[article_id]
            for chunk in article_chunks:
                tasks.append(contextualize_one(article, chunk))
        contextualized.extend(await asyncio.gather(*tasks))
        return contextualized
