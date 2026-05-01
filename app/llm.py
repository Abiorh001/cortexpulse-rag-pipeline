from openai import AsyncOpenAI

from app.config import Settings
from app.models import Article, ArticleChunk, Citation
from app.prompts import PromptCatalog, get_prompts
from app.reliability import CircuitBreaker, retry_with_backoff


class OpenAIService:
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for embeddings and answers")
        self.settings = settings
        self.prompts: PromptCatalog = get_prompts()
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.request_timeout_seconds,
        )
        self.breaker = CircuitBreaker(
            name="openai",
            failure_threshold=settings.circuit_breaker_failure_threshold,
            reset_seconds=settings.circuit_breaker_reset_seconds,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        response = await retry_with_backoff(
            lambda: self.client.embeddings.create(
                model=self.settings.openai_embedding_model,
                input=texts,
            ),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )
        return [item.embedding for item in response.data]

    async def contextualize_chunk(self, article: Article, chunk_text: str) -> str:
        article_excerpt = article.body[: self.settings.max_article_context_chars]
        prompt = self.prompts.contextualize.user_template.format(
            title=article.title,
            article_excerpt=article_excerpt,
            chunk_text=chunk_text,
        )
        response = await retry_with_backoff(
            lambda: self.client.chat.completions.create(
                model=self.settings.openai_chat_model,
                temperature=self.settings.openai_contextualize_temperature,
                messages=[
                    {
                        "role": "system",
                        "content": self.prompts.contextualize.system,
                    },
                    {"role": "user", "content": prompt},
                ],
            ),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )
        return response.choices[0].message.content.strip()

    async def answer_question(
        self, question: str, chunks: list[ArticleChunk], citations: list[Citation]
    ) -> str:
        if not chunks:
            return "I could not find relevant ingested news content to answer that."

        context_blocks = []
        for index, chunk in enumerate(chunks, start=1):
            context_blocks.append(
                f"[{index}] Title: {chunk.title}\n"
                f"Source: {chunk.source}\n"
                f"URL: {chunk.url}\n"
                f"Text: {chunk.text}"
            )
        context = "\n\n".join(context_blocks)
        prompt = self.prompts.answer.user_template.format(
            question=question,
            context=context,
        )

        response = await retry_with_backoff(
            lambda: self.client.chat.completions.create(
                model=self.settings.openai_chat_model,
                temperature=self.settings.openai_answer_temperature,
                messages=[
                    {"role": "system", "content": self.prompts.answer.system},
                    {"role": "user", "content": prompt},
                ],
            ),
            attempts=self.settings.retry_attempts,
            initial_backoff_seconds=self.settings.retry_initial_backoff_seconds,
            backoff_multiplier=self.settings.retry_backoff_multiplier,
            circuit_breaker=self.breaker,
        )
        return response.choices[0].message.content.strip()
