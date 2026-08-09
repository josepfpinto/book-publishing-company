"""FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.deps import lifespan
from api.routes.books import router as books_router
from api.routes.chat import router as chat_router

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://frontend:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}
