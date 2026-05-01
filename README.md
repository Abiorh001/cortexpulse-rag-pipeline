# CortexPulse Intelligence Pipeline

CortexPulse is a lightweight end-to-end news intelligence pipeline built for the Synapse AI technical assessment.

It ingests news articles, splits them into retrieval-friendly chunks, embeds them with OpenAI, stores them in Qdrant, and exposes a simple FastAPI RAG interface that returns answers with traceable sources.

The primary data source is the Guardian Open Platform. If the API is unavailable or no key is provided, the system falls back to bundled sample articles so the pipeline can still run locally end to end.

## What It Does

- Ingests news articles from Guardian API or fallback data.
- Splits articles into paragraph and sentence-aware chunks.
- Embeds and stores chunks with metadata in Qdrant.
- Exposes `/api/ingest` and `/api/chat` endpoints.
- Returns answers grounded in retrieved content with source attribution.
- Rebuilds the vector collection on each ingest and tags chunks with a fresh run ID/timestamp so chat only searches the latest run.

## How It Works

### 1. Ingestion

- `POST /api/ingest`
- Fetches one Guardian article by default for a fast assessment demo.
- Falls back to `data/sample_articles.json` when Guardian is unavailable.
- Filters out weak live-blog style Guardian results before indexing.
- Splits content with configurable `CHUNK_SIZE=400` and `CHUNK_OVERLAP=200`.

### 2. Embedding And Storage

- Embeds chunks using `text-embedding-3-small`.
- Stores vectors in Qdrant with title, URL, source, timestamp, and chunk text.
- Resets the `cortexpulse_news` Qdrant collection during ingest to avoid mixing old and new runs.

### 3. Retrieval And Answering

- `POST /api/chat`
- Embeds the user question.
- Retrieves top-K semantically relevant chunks.
- Sends the question plus retrieved context to OpenAI.
- Returns the answer with source citations.

## Running Locally

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Create an environment file:

```bash
cp .env.example .env
```

Set at least:

```bash
OPENAI_API_KEY=your_key_here
```

`GUARDIAN_API_KEY` is optional. Without it, the app uses bundled fallback articles.

Install packages:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run the app and Qdrant:

```bash
docker compose up --build
```

Open:

```text
http://localhost:8000
```

Click **Ingest news**, then ask a question.

You can also test the API directly:

```bash
curl -X POST http://localhost:8000/api/ingest

curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How is the Pentagon planning to use AI companies in the US military?"}'
```

The chat response includes a clean `sources` list:

```json
{
  "answer": "...",
  "sources": [
    {
      "title": "...",
      "url": "...",
      "source": "The Guardian",
      "published": "..."
    }
  ]
}
```

## Configuration

Key environment variables:

- `OPENAI_API_KEY`: required.
- `GUARDIAN_API_KEY`: optional.
- `OPENAI_CHAT_MODEL`: default `gpt-4o-mini`.
- `OPENAI_EMBEDDING_MODEL`: default `text-embedding-3-small`.
- `QDRANT_URL`: default `http://localhost:6333` locally and `http://qdrant:6333` in Docker.
- `RETRIEVAL_TOP_K`: default `4`.
- `RETRIEVAL_SCORE_THRESHOLD`: default `0.3`.
- `CHUNK_SIZE`: default `400`.
- `CHUNK_OVERLAP`: default `200`.
- `MAX_ARTICLES`: default `1`.
- `CONTEXTUALIZATION_ENABLED`: default `false`.

Non-secret defaults live in `config.yaml`. Environment variables override them.

## Design Decisions

- **Guardian API + fallback data**: satisfies the public news source requirement while keeping the demo reliable without a news API key.
- **Qdrant**: lightweight local vector database that runs cleanly through Docker Compose.
- **OpenAI embeddings and generation**: keeps the implementation small and easy to run.
- **Collection reset + run ID on ingest**: each UI ingest reflects a fresh pipeline run instead of reusing stale vectors.
- **No hybrid search or reranker by default**: intentionally excluded to keep the system aligned with the lightweight assessment brief.
- **Contextual chunk enrichment is optional**: the hook exists via `CONTEXTUALIZATION_ENABLED=true`, but the default path is faster and more predictable for a timed demo.

## Failure Handling

- Retry with exponential backoff for Guardian, OpenAI, and Qdrant calls.
- Basic circuit breaker to avoid repeatedly calling failing services.
- Guardian article filtering to avoid indexing weak live-blog placeholder content.
- Retrieval score threshold to avoid answering from weak or irrelevant chunks.
- Bundled fallback dataset so ingestion can still complete locally.

## One Thing I Would Do Differently

Given more time, I would add a lightweight evaluation layer before adding retrieval complexity. It would include:

- A fixed query set with expected source references.
- Retrieval quality metrics such as MRR and mean rank.
- Citation coverage checks.
- Latency, cost, and total API/LLM call tracking.
- A grounding gate to reject answers not supported by retrieved chunks.

Once evaluation is in place, I would improve retrieval with hybrid search, RAG fusion, and optional reranking only if those changes show measurable gains.
