import os

# Deterministic fake embeddings keep tests fast; test_semantic.py loads the real model itself
os.environ.setdefault("EMBEDDINGS", "fake")
