import os

# Deterministic fake embeddings keep tests fast; test_semantic.py loads the real model itself
os.environ.setdefault("EMBEDDINGS", "fake")
# Keep tests offline and free even when a local .env sets LLM_MODEL (load_dotenv won't override this)
os.environ["LLM_MODEL"] = ""
