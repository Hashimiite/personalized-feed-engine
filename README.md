# Personalized feed engine

[![CI](https://github.com/Hashimiite/personalized-feed-engine/actions/workflows/ci.yml/badge.svg)](https://github.com/Hashimiite/personalized-feed-engine/actions/workflows/ci.yml)

A FastAPI service that ranks posts for each user, caches feeds in Redis, and pushes updates over WebSockets.

## How ranking works

Each post gets a score from four signals, then the list is diversified so one topic can't take over:

| Signal | Weight |
|---|---|
| Interest match with the user's topics | 0.4 |
| Post quality | 0.3 |
| Recency (decays by the hour) | 0.2 |
| Clicks on the post | 0.1 per click |

Feeds are cached in Redis for 60 seconds and invalidated when the user clicks a post. When a new post is created, every interested user's feed is recomputed and pushed to their open WebSocket connections.

## Run it

Requires Docker.

```bash
docker compose up -d --build --wait
docker compose exec api python seed.py
curl localhost:8000/feed/1
```

Open `index.html` in a browser for a simple feed UI. Stop everything with `docker compose down -v`.

## API

| Method | Path | What it does |
|---|---|---|
| GET | `/feed/{user_id}` | Ranked feed (served from cache when fresh) |
| POST | `/interact/{user_id}/{post_id}` | Record a click and invalidate that user's cache |
| POST | `/posts?content=&topic=&quality=` | Create a post and notify interested users |
| GET | `/posts` | All posts |
| WS | `/ws/{user_id}` | Live feed updates |
| GET | `/health` | Liveness check |

## Development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
ruff check . && ruff format --check .
pytest                      # unit tests run anywhere
```

Integration tests in `tests/test_api.py` run when `DATABASE_URL` points at a Postgres instance (with Redis on `REDIS_HOST`/`REDIS_PORT`); otherwise they're skipped. CI runs them against Postgres 17 and Redis 7 service containers.

Load test with Locust while the stack is running:

```bash
locust -f locustfile.py --host http://localhost:8000
```

## CI

GitHub Actions runs on every push and pull request:

1. **lint**: ruff check and format
2. **test**: unit and integration tests against Postgres and Redis
3. **docker**: builds the image, starts the full Compose stack, seeds it, and checks `/health` and `/feed`
