# CortexPulse Intelligence Pipeline

CortexPulse is a minimal news intelligence pipeline for the Synapse AI technical assessment. It ingests news articles, splits them into retrieval-friendly chunks, embeds them with OpenAI, stores them in Qdrant, and exposes a simple FastAPI chat interface that returns sourced answers.

The primary news source is The Guardian Open Platform. If `GUARDIAN_API_KEY` is missing or the API is unavailable, the app falls back to bundled sample articles so the local demo still works end to end.

## How it works

1. `POST /api/ingest` fetches Guardian articles or bundled fallback articles.
2. Article bodies are split with a recursive text splitter using configurable paragraph and sentence-aware chunking.
3. Chunks are embedded and stored with source metadata. Optional contextual chunk enrichment can be enabled with `CONTEXTUALIZATION_ENABLED=true`; prompt templates live in `app/prompts.py`.
4. Enriched chunks are embedded with `text-embedding-3-small` and stored in Qdrant.
5. `POST /api/chat` embeds the user question, retrieves relevant chunks, and asks OpenAI to answer only from those chunks.
6. The browser UI at `http://localhost:8000` provides an ingest button and a simple chat interface with citations.

External calls to Guardian, OpenAI, and Qdrant use configurable retry/backoff settings plus a small circuit breaker so transient failures are handled deliberately without making the code heavy.

The default path intentionally keeps contextual enrichment off so the assessment demo stays fast and predictable. The hook is still present: set `CONTEXTUALIZATION_ENABLED=true` to prepend Anthropic-style chunk context before embeddings. I did not enable hybrid search, RAG fusion, or a reranker in the MVP because the brief asks for a lightweight end-to-end pipeline, not a retrieval research system.

## How to run

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create your environment file:

```bash
cp .env.example .env
```

Edit `.env` and set at least:

```bash
OPENAI_API_KEY=your_openai_api_key_here
```

`GUARDIAN_API_KEY` is optional. Without it, the app uses bundled sample articles.

Install dependencies locally with `uv`:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run the full app with Qdrant:

```bash
docker compose up --build
```

The Compose stack pins Qdrant server `v1.17.1` to match the locked `qdrant-client` version, leaving the client's compatibility check enabled.

Open:

```text
http://localhost:8000
```

Click **Ingest news**, then ask a question such as:

```text
How are AI systems being used in hospitals?
```

## Configuration

Important environment variables:

- `OPENAI_API_KEY`: required for embeddings and answers.
- `GUARDIAN_API_KEY`: optional Guardian Open Platform key.
- `OPENAI_CHAT_MODEL`: defaults to `gpt-4o-mini`.
- `OPENAI_EMBEDDING_MODEL`: defaults to `text-embedding-3-small`.
- `QDRANT_URL`: defaults to `http://localhost:6333` locally and `http://qdrant:6333` in Docker.
- `GUARDIAN_QUERY`: defaults to `artificial intelligence`.
- `MAX_ARTICLES`: defaults to `1` for a fast assessment demo.
- `CHUNK_SIZE`: defaults to `400`.
- `CHUNK_OVERLAP`: defaults to `200`.
- `CONTEXTUALIZATION_ENABLED`: defaults to `false`; set to `true` to add Anthropic-style contextual chunk enrichment before embedding.
- `RETRIEVAL_TOP_K`: defaults to `4`.
- `OPENAI_ANSWER_TEMPERATURE`: defaults to `0.2`.
- `OPENAI_CONTEXTUALIZE_TEMPERATURE`: defaults to `0`.
- `RETRY_ATTEMPTS`, `RETRY_INITIAL_BACKOFF_SECONDS`, `RETRY_BACKOFF_MULTIPLIER`: tune retry behavior.
- `CIRCUIT_BREAKER_FAILURE_THRESHOLD`, `CIRCUIT_BREAKER_RESET_SECONDS`: tune circuit breaker behavior.

Non-secret defaults live in `config.yaml`. Prompt templates live in `app/prompts.py`. Environment variables override the config values for local or deployment-specific changes.

## One thing I would do differently with more time

I would add a small evaluation pipeline before adding more retrieval complexity. That would include a fixed question set, expected source references, mean reciprocal rank/mean rank for retrieval quality, citation coverage, total API/LLM call counts, latency, and a grounding or hallucination gate that rejects answers not supported by retrieved chunks. After that, I would add BM25 + vector hybrid search, optional RAG fusion for multiple query rewrites, and a lightweight reranker only if the evals show measurable improvement. I intentionally kept those out of the default implementation because this submission prioritizes a reliable local run, traceable citations, and code that can be reviewed quickly.
