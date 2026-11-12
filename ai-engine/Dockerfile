FROM python:3.12.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
ENV MODEL_CACHE=/models
COPY app app
COPY tests tests
RUN python -c "from app.retrieval import model; model()"
RUN useradd --uid 10001 --create-home worker
USER worker
ENV HF_HUB_OFFLINE=1
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
