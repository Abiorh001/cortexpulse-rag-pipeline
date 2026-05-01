from functools import lru_cache

from pydantic import BaseModel


class PromptTemplate(BaseModel):
    system: str
    user_template: str


class PromptCatalog(BaseModel):
    contextualize: PromptTemplate
    answer: PromptTemplate


@lru_cache
def get_prompts() -> PromptCatalog:
    return PromptCatalog(
        contextualize=PromptTemplate(
            system="You write compact context that improves retrieval.",
            user_template=(
                "Give a concise retrieval context for the chunk below.\n"
                "Explain what the chunk is about and how it fits into the article.\n"
                "Use 2 short sentences maximum.\n\n"
                "Article title: {title}\n"
                "Article body excerpt:\n{article_excerpt}\n\n"
                "Chunk:\n{chunk_text}"
            ),
        ),
        answer=PromptTemplate(
            system=(
                "Answer using only the supplied news context. "
                "If the context is insufficient, say so. "
                "Cite sources inline as [1], [2], etc."
            ),
            user_template="Question: {question}\n\nNews context:\n{context}",
        ),
    )
