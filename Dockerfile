FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 HF_HUB_DISABLE_TELEMETRY=1

WORKDIR /srv

# CPU only torch first (the default wheel pulls gigabytes of GPU libraries), then the rest
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu
COPY requirements-demo.txt .
RUN pip install -r requirements-demo.txt

# Bake the embedding model into the image so the container never downloads at runtime
RUN python -c "from sentence_transformers import SentenceTransformer as S; S('sentence-transformers/all-MiniLM-L6-v2').save('/models/all-MiniLM-L6-v2')"
ENV EMBEDDING_MODEL=/models/all-MiniLM-L6-v2 HF_HUB_OFFLINE=1

COPY rag ./rag
COPY app ./app

RUN useradd --create-home appuser
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"

CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]
