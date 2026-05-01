from pydantic import BaseModel, Field, HttpUrl


class Article(BaseModel):
    id: str
    title: str
    url: str
    source: str
    published_at: str | None = None
    body: str


class ArticleChunk(BaseModel):
    id: str
    run_id: str | None = None
    article_id: str
    title: str
    url: str
    source: str
    published_at: str | None = None
    chunk_index: int
    text: str
    contextual_text: str


class Citation(BaseModel):
    title: str
    url: str
    source: str
    snippet: str
    score: float | None = None


class IngestResponse(BaseModel):
    source: str
    articles_loaded: int
    chunks_indexed: int
    collection: str
    run_id: str
    article_titles: list[str]
    message: str


class ChatRequest(BaseModel):
    question: str = Field(min_length=3)


class ChatResponse(BaseModel):
    answer: str
    citations: list[Citation]


class HealthResponse(BaseModel):
    status: str
    collection: str
