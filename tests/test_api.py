"""Integration tests: need Postgres and Redis (docker compose, or the CI service containers)."""

import os
import time

import pytest

if not os.getenv("DATABASE_URL"):
    pytest.skip("DATABASE_URL not set; integration tests need Postgres and Redis", allow_module_level=True)

from fastapi.testclient import TestClient

from db import SessionLocal, engine, init_db
from embeddings import get_embeddings, post_text
from feed.core import rc
from main import app
from models import Base, Post, User


@pytest.fixture(autouse=True)
def seeded():
    Base.metadata.drop_all(bind=engine)
    init_db()
    rc.flushdb()
    db = SessionLocal()
    db.add(User(id=1, interests="tech,ai"))
    now = time.time()
    for i, topic in enumerate(["tech", "ai", "finance", "sports", "tech", "ai"]):
        content = f"post {i}"
        vector = get_embeddings().embed_query(post_text(topic, content))
        db.add(Post(content=content, topic=topic, quality=0.5, timestamp=now - i * 600, embedding=vector))
    db.commit()
    db.close()
    yield


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    assert client.get("/health").json() == {"ok": True}


def test_feed_is_computed_then_served_from_cache(client):
    first = client.get("/feed/1").json()
    assert first["source"] == "computed"
    ids = [p["id"] for p in first["data"]]
    assert ids and len(ids) == len(set(ids))
    assert client.get("/feed/1").json()["source"] == "cache"


def test_click_invalidates_cached_feed(client):
    client.get("/feed/1")
    assert client.post("/interact/1/1").status_code == 200
    assert client.get("/feed/1").json()["source"] == "computed"


def test_new_post_is_pushed_over_websocket(client):
    with client.websocket_connect("/ws/1") as ws:
        res = client.post("/posts", params={"content": "fresh", "topic": "ai", "quality": 0.9})
        assert res.status_code == 200
        message = ws.receive_json()
    assert message["type"] == "feed_update"
    assert any(p["id"] == res.json()["id"] for p in message["data"])


def test_new_post_is_stored_with_an_embedding(client):
    res = client.post("/posts", params={"content": "vector test", "topic": "ai", "quality": 0.5})
    post_id = res.json()["id"]
    db = SessionLocal()
    stored = db.get(Post, post_id)
    db.close()
    assert len(stored.embedding) == 384
