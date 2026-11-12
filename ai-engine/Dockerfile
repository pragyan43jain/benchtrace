FROM python:3.12.10-slim
WORKDIR /app
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
ENV MODEL_CACHE=/models
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5',cache_dir='/models',threads=2)"
COPY app app
COPY tests tests
COPY evaluation evaluation
RUN useradd --uid 10001 --create-home worker && mkdir -p /uploads && chown worker /uploads
USER worker
ENV HF_HUB_OFFLINE=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
