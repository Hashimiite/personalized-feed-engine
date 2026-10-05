# Personalized feed engine

[![CI](https://github.com/Hashimiite/personalized-feed-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/Hashimiite/personalized-feed-engine/actions/workflows/ci.yml)

A FastAPI service that ranks posts for each user by meaning rather than keywords, caches feeds in Redis, pushes new posts over WebSockets and answers questions about the feed with a LangGraph assistant.

## How ranking works

Every post is embedded with [BAAI/bge-small-en-v1.5](https://huggingface.co/BAAI/bge-small-en-v1.5) (384 dimensions, run locally through FastEmbed behind LangChain's `Embeddings` interface) and stored in a pgvector column.

Each user gets a profile vector that averages their stated interests with the posts they clicked most recently. pgvector returns the 200 posts closest to that profile, and each one is scored:

| Signal | Weight |
|---|---|
| Semantic similarity between the user profile and the post | 0.4 |
| Post quality | 0.3 |
| Recency (decays by the hour) | 0.2 |
| Clicks on the post | 0.1 per click |

The feed is then diversified so one topic can't take over. Because relevance comes from meaning, a user interested in "machine learning" sees research posts about neural networks even though "research" is not one of their topics. Clicking posts moves the profile toward them, so the feed adapts as people use it.

Feeds are cached in Redis for 60 seconds and invalidated on every click. New posts are pushed over WebSockets to users who listed the topic or whose profile is close in meaning to the post.

## Feed assistant

`POST /ask` runs a LangGraph pipeline:

```
retrieve (semantic search in pgvector)
   ├── nothing above 0.5 similarity → no_match: "No posts in the feed match that question yet."
   └── otherwise → generate: answer from the retrieved posts only, citing them as [id]
```

Set `LLM_MODEL` to any LangChain chat model in `.env` to get written answers, for example `openai:gpt-4o-mini` with `OPENAI_API_KEY`, or `anthropic:claude-haiku-4-5-20251001` with `ANTHROPIC_API_KEY`. Docker Compose passes both through to the API. Without one, or if the model call fails, the assistant lists the most relevant posts, so the endpoint always responds.

The 0.5 threshold was calibrated on the seeded posts: related questions score 0.59 and above, while unrelated ones (recipes, car repair, weather) stay at 0.455 or below.

```bash
curl -X POST localhost:8000/ask -H 'content-type: application/json' \
  -d '{"question": "Did interest rates change?"}'
```

## Run it

Requires Docker. The image downloads the embedding model at build time.

```bash
docker compose up -d --build --wait
docker compose exec api python seed.py
curl localhost:8000/feed/1
```

Open `index.html` in a browser for a simple feed UI. Stop everything with `docker compose down -v`.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/feed/{user_id}` | Semantically ranked feed (served from cache when fresh) |
| POST | `/ask` | Answer a question from the feed's posts (`{"question": "..."}`, 3 to 500 characters) |
| POST | `/interact/{user_id}/{post_id}` | Record a click and invalidate that user's cache |
| POST | `/posts?content=&topic=&quality=` | Create and embed a post, then notify interested users |
| GET | `/posts` | All posts |
| WS | `/ws/{user_id}` | Live feed updates |
| GET | `/health` | Liveness check |

## Configuration

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | built from `DB_*` | Postgres with the pgvector extension |
| `REDIS_HOST`, `REDIS_PORT` | `localhost`, `6379` | Feed cache |
| `LLM_MODEL` | unset | LangChain chat model for `/ask` answers, e.g. `openai:gpt-4o-mini` |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY` | unset | Key for the provider named in `LLM_MODEL` |
| `ASK_MIN_SIMILARITY` | `0.5` | Similarity a post needs to count as relevant |
| `EMBEDDINGS` | real model | Set to `fake` for LangChain's deterministic test embeddings |

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest
```

Unit tests and the assistant graph tests run anywhere. Tests in `tests/test_api.py` and `tests/test_semantic.py` need `DATABASE_URL` pointing at Postgres with pgvector and Redis on `REDIS_HOST`/`REDIS_PORT`; otherwise they're skipped. `test_semantic.py` loads the real model and checks that interests surface posts by meaning, that clicks pull similar posts up, and that the assistant answers related questions and declines unrelated ones.

Load test with Locust while the stack is running:

```bash
locust -f locustfile.py --host http://localhost:8000
```

## CI

GitHub Actions runs on every push and pull request:

1. **lint**: ruff check and format
2. **test**: unit, graph, API and real model tests against pgvector Postgres and Redis
3. **docker**: builds the image, starts the full Compose stack, seeds it, and checks `/health`, `/feed` and that `/ask` answers an interest rate question with finance posts

The image is about 1 GB because it ships the ONNX runtime and the embedding model so it can run fully offline.
