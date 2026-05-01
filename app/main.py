from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.models import ChatRequest, ChatResponse, HealthResponse, IngestResponse
from app.pipeline import CortexPulsePipeline

app = FastAPI(title="CortexPulse Intelligence Pipeline")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@lru_cache
def get_pipeline() -> CortexPulsePipeline:
    return CortexPulsePipeline(get_settings())


@app.get("/", include_in_schema=False)
async def index() -> FileResponse:
    return FileResponse("app/static/index.html")


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", collection=settings.qdrant_collection)


@app.post("/api/ingest", response_model=IngestResponse)
async def ingest() -> IngestResponse:
    try:
        return await get_pipeline().ingest()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        return await get_pipeline().chat(request.question)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
