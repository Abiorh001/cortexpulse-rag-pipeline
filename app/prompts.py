import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel


class PromptTemplate(BaseModel):
    system: str
    user_template: str


class PromptCatalog(BaseModel):
    contextualize: PromptTemplate
    answer: PromptTemplate


@lru_cache
def get_prompts() -> PromptCatalog:
    prompt_path = Path(os.getenv("CORTEXPULSE_PROMPTS", "prompts.yaml"))
    with prompt_path.open("r", encoding="utf-8") as file:
        data: dict[str, Any] = yaml.safe_load(file) or {}
    return PromptCatalog.model_validate(data)
