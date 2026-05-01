import pytest

from app.config import Settings
from app.pipeline import CortexPulsePipeline


class FakeLLM:
    async def contextualize_chunk(self, article, chunk_text):
        return f"Context for {article.title}"

    async def embed_texts(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    async def answer_question(self, question, chunks, citations):
        return "Mock answer [1]"


class FakeStore:
    def __init__(self):
        self.indexed = []

    async def upsert_chunks(self, chunks, embeddings, *, reset=False):
        self.indexed = chunks
        self.reset = reset
        return len(chunks)

    async def search(self, query_embedding):
        return [], []


@pytest.mark.asyncio
async def test_ingest_uses_sample_fallback_without_guardian_key():
    settings = Settings(
        OPENAI_API_KEY="test-key",
        GUARDIAN_API_KEY="",
        CHUNK_SIZE=400,
        CHUNK_OVERLAP=200,
    )
    pipeline = CortexPulsePipeline.__new__(CortexPulsePipeline)
    pipeline.settings = settings
    pipeline.llm = FakeLLM()
    pipeline.store = FakeStore()

    result = await pipeline.ingest()

    assert result.source == "sample"
    assert result.articles_loaded >= 1
    assert result.chunks_indexed >= 1
    assert pipeline.store.indexed[0].contextual_text == pipeline.store.indexed[0].text


@pytest.mark.asyncio
async def test_ingest_can_enable_contextualization():
    settings = Settings(
        OPENAI_API_KEY="test-key",
        GUARDIAN_API_KEY="",
        CHUNK_SIZE=400,
        CHUNK_OVERLAP=200,
        CONTEXTUALIZATION_ENABLED=True,
    )
    pipeline = CortexPulsePipeline.__new__(CortexPulsePipeline)
    pipeline.settings = settings
    pipeline.llm = FakeLLM()
    pipeline.store = FakeStore()

    await pipeline.ingest()

    assert pipeline.store.indexed[0].contextual_text.startswith("Context for")
