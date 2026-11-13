FROM python:3.12.10-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr=5.3.0-2 tesseract-ocr-eng=1:4.1.0-2 && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements.lock ./
RUN pip install --no-cache-dir -r requirements.lock
ENV MODEL_CACHE=/models
COPY model.lock.json prefetch_model.py ./
RUN python prefetch_model.py && chmod -R a+rX /models
COPY app app
COPY tests tests
COPY evaluation evaluation
RUN useradd --uid 10001 --create-home worker && mkdir -p /uploads && chown worker /uploads
USER worker
ENV HF_HUB_OFFLINE=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
