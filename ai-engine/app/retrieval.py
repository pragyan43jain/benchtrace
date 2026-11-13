"""Local semantic embeddings with explicit model identity; no silent fallbacks."""
import os
from functools import lru_cache
from pathlib import Path

MODEL='BAAI/bge-small-en-v1.5'
REVISION='aa8f8b060edb00e03bfdd08813a2949946c8ba55'
def embedding_version():
    return 'lexical-sha256-v1' if os.getenv('EMBEDDING_MODE')=='lexical' else MODEL+'@'+REVISION
@lru_cache(maxsize=1)
def model():
    from fastembed import TextEmbedding
    cache=os.getenv('MODEL_CACHE','/models')
    marker=Path(cache)/'model-path'
    options={'specific_model_path':marker.read_text().strip()} if marker.exists() else {}
    return TextEmbedding(model_name=MODEL,cache_dir=cache,threads=2,local_files_only=os.getenv("HF_HUB_OFFLINE")=="1",**options)

def semantic_embed(text):
    return next(model().embed([text])).tolist()
