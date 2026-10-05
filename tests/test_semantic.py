"""Semantic behavior with the real embedding model (downloads about 70 MB on first run)."""

import os
import time

import pytest

if not os.getenv("DATABASE_URL"):
    pytest.skip("DATABASE_URL not set; semantic tests need Postgres with pgvector", allow_module_level=True)

from db import SessionLocal, engine, init_db
from embeddings import FastEmbedEmbeddings, post_text
from feed.core import generate_feed, semantic_search
from models import Base, Interaction, Post, User

POSTS = [
    ("research", "Neural networks learn to predict protein folding from sequence alone"),
    ("ai", "Small language models match larger ones on reasoning benchmarks"),
    ("sports", "Hockey playoffs open with two overtime games"),
    ("sports", "Hockey goalie sets new shutout record"),
    ("finance", "Bond yields fall as inflation cools"),
    ("tech", "Rust adoption grows in Linux kernel drivers"),
]


@pytest.fixture(scope="module")
def real():
    return FastEmbedEmbeddings()


@pytest.fixture(autouse=True)
def seeded(real):
    Base.metadata.drop_all(bind=engine)
    init_db()
    db = SessionLocal()
    db.add(User(id=1, interests="machine learning"))
    vectors = real.embed_documents([post_text(t, c) for t, c in POSTS])
    now = time.time()
    for (topic, content), vector in zip(POSTS, vectors, strict=True):
        # Equal quality and age so ranking differences come from meaning alone
        db.add(Post(content=content, topic=topic, quality=0.5, timestamp=now, embedding=vector))
    db.commit()
    db.close()


def topics(feed):
    return [p.topic for p in feed]


def test_feed_ranks_by_meaning_not_topic_labels(real):
    db = SessionLocal()
    feed = generate_feed(db, 1, embeddings=real)
    db.close()
    # "research" never appears in the user's interests, but it is about machine learning
    assert set(topics(feed)[:2]) == {"research", "ai"}
    assert topics(feed)[-1] != "research"


def test_clicks_pull_similar_posts_up(real):
    db = SessionLocal()
    before = topics(generate_feed(db, 1, embeddings=real)).index("sports")
    hockey = db.query(Post).filter(Post.topic == "sports").all()
    db.add_all(Interaction(user_id=1, post_id=p.id, type="click") for p in hockey)
    db.commit()
    after = topics(generate_feed(db, 1, embeddings=real)).index("sports")
    db.close()
    assert after < before


def test_semantic_search_finds_posts_by_meaning(real):
    db = SessionLocal()
    results = semantic_search(db, "how do proteins fold", k=2, embeddings=real)
    db.close()
    top, similarity = results[0]
    assert "protein" in top.content
    assert similarity > results[1][1]
