"""Batch embedding helper for Azure OpenAI text-embedding-3-large."""
from __future__ import annotations

import math
import os
import sys

from dotenv import load_dotenv
from openai import AzureOpenAI

load_dotenv()


def embed_texts(texts: list[str], batch_size: int = 100) -> list[list[float]]:
    """Embed a list of texts via Azure OpenAI in batches.
    Returns a flat list of embedding vectors in the same order as input."""
    client = AzureOpenAI(
        azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
    )
    deployment = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
    result: list[list[float]] = []
    total_batches = math.ceil(len(texts) / batch_size)
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        print(f"Embedding batch {i // batch_size + 1}/{total_batches}...", file=sys.stderr)
        response = client.embeddings.create(input=batch, model=deployment)
        result.extend(d.embedding for d in sorted(response.data, key=lambda d: d.index))
    return result
