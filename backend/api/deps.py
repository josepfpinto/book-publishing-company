"""FastAPI lifespan: ChromaDB collection + AzureOpenAI client singletons."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import chromadb
from dotenv import load_dotenv
from fastapi import FastAPI
from openai import AzureOpenAI

load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.chroma_collection = chromadb.PersistentClient(
        path="./data/chroma"
    ).get_or_create_collection("books")
    app.state.openai_client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )
    app.state.openai_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    app.state.openai_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    yield
