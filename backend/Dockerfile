FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# INSTALL_DEV=true adds pytest — used by the `backend-test` compose service.
# Default false keeps the test framework out of the runtime image.
ARG INSTALL_DEV=false

COPY backend/requirements.txt backend/requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && if [ "$INSTALL_DEV" = "true" ]; then \
         pip install --no-cache-dir -r requirements-dev.txt; \
       fi

# JSON array form required — source directory name contains a space
COPY ["books shared/", "/app/books/"]

COPY backend/ .

RUN useradd --create-home appuser \
    && mkdir -p /app/data/chroma \
    && chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
