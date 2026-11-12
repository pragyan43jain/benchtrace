"""Local semantic embeddings with explicit model identity; no silent fallbacks."""
import os
from functools import lru_cache

MODEL='BAAI/bge-small-en-v1.5'
@lru_cache(maxsize=1)
def model():
    from fastembed import TextEmbedding
    return TextEmbedding(model_name=MODEL,cache_dir=os.getenv('MODEL_CACHE','/models'),threads=2,local_files_only=os.getenv("HF_HUB_OFFLINE")=="1")

def semantic_embed(text):
    return next(model().embed([text])).tolist()
