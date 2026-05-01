from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import Distance, FieldCondition, Filter, MatchValue
from qdrant_client.models import PointStruct, VectorParams

from app.config import Settings
from app.models import ArticleChunk, Citation
from app.reliability import CircuitBreaker, retry_with_backoff


class QdrantStore:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = AsyncQdrantClient(
            url=settings.qdrant_url,
            timeout=settings.request_timeout_seconds,
        )
        self.breaker = CircuitBreaker(
            name="qdrant",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            reset_seconds=settings.circuit_breaker_reset_seconds,
        )

    async def ensure_collection(self, vector_size: int) -> None:
        collections = await retry_with_backoff(
            self.client.get_collections,
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )
        names = {collection.name for collection in collections.collections}
        if self.settings.qdrant_collection in names:
            return
        await retry_with_backoff(
            lambda: self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            ),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )

    async def reset_collection(self, vector_size: int) -> None:
        exists = await retry_with_backoff(
            lambda: self.client.collection_exists(self.settings.qdrant_collection),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )
        if exists:
            await retry_with_backoff(
                lambda: self.client.delete_collection(self.settings.qdrant_collection),
                attempts=self.settings.retry_attempts,
                initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
                backoff_multiplier=self.settings.retry_backoff_multiplier,
                circuit_breaker=self.breaker,
            )
        await retry_with_backoff(
            lambda: self.client.create_collection(
                collection_name=self.settings.qdrant_collection,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            ),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )

    async def upsert_chunks(
        self, chunks: list[ArticleChunk], embeddings: list[list[float]], *, reset: bool = False
    ) -> int:
        if not chunks:
            return 0
        if reset:
            await self.reset_collection(len(embeddings[0]))
        else:
            await self.ensure_collection(len(embeddings[0]))
        points = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            points.append(
                PointStruct(
                    id=chunk.id,
                    vector=embedding,
                    payload=chunk.model_dump(),
                )
            )
        await retry_with_backoff(
            lambda: self.client.upsert(
                collection_name=self.settings.qdrant_collection,
                points=points,
                wait=True,
            ),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )
        return len(points)

    async def search(
        self, query_embedding: list[float], limit: int = 4, run_id: str | None = None
    ) -> tuple[list[ArticleChunk], list[Citation]]:
        exists = await retry_with_backoff(
            lambda: self.client.collection_exists(self.settings.qdrant_collection),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )
        if not exists:
            return [], []

        query_filter = None
        if run_id:
            query_filter = Filter(
                must=[FieldCondition(key="run_id", match=MatchValue(value=run_id))]
            )

        response = await retry_with_backoff(
            lambda: self.client.query_points(
                collection_name=self.settings.qdrant_collection,
                query=query_embedding,
                query_filter=query_filter,
                limit=limit,
                with_payload=True,
            ),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )

        chunks: list[ArticleChunk] = []
        citations: list[Citation] = []
        seen_urls: set[str] = set()
        for result in response.points:
            if result.score is not None and result.score < self.settings.retrieval_score_threshold:
                continue
            payload = result.payload or {}
            chunk = ArticleChunk.model_validate(payload)
            chunks.append(chunk)
            if chunk.url in seen_urls:
                continue
            seen_urls.add(chunk.url)
            citations.append(
                Citation(
                    title=chunk.title,
                    url=chunk.url,
                    source=chunk.source,
                    published=chunk.published_at,
                    snippet=chunk.text[: self.settings.citation_snippet_chars],
                    score=result.score,
                )
            )
        return chunks, citations
