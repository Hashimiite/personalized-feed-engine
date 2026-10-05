"""Seed one demo user and 24 posts with real headlines, embedded for semantic ranking."""

import random
import time

from db import SessionLocal, init_db
from embeddings import get_embeddings, post_text
from models import Interaction, Post, User

POSTS = {
    "ai": [
        "New paper shows small language models can match larger ones on reasoning",
        "Open source vision model tops image classification benchmark",
        "Researchers cut transformer training cost with sparse attention",
        "How retrieval augmented generation reduces hallucinations",
    ],
    "research": [
        "Neural networks learn to predict protein folding from sequence alone",
        "Study finds deep learning models memorize rare training examples",
        "Reinforcement learning agent beats experts at chip layout design",
        "Graph neural networks speed up drug discovery screening",
    ],
    "tech": [
        "Postgres 18 adds asynchronous I/O for faster reads",
        "Browser vendors agree on a shared web component standard",
        "Rust adoption grows in Linux kernel drivers",
        "Edge computing brings lower latency to mobile apps",
    ],
    "startups": [
        "Seed funding rebounds for developer tools companies",
        "Small team ships analytics product to ten thousand users",
        "Founders share lessons from pivoting a hardware startup",
        "Remote first startups report higher retention",
    ],
    "finance": [
        "Central bank holds interest rates steady for third quarter",
        "Bond yields fall as inflation cools",
        "Bank stocks rally after strong earnings reports",
        "Mortgage rates dip to their lowest level this year",
    ],
    "sports": [
        "Hockey playoffs open with two overtime games",
        "Basketball rookie sets scoring record in debut",
        "Soccer club signs veteran striker on free transfer",
        "Marathon runner breaks course record in Boston",
    ],
}


def seed():
    init_db()
    db = SessionLocal()
    db.query(Interaction).delete()
    db.query(Post).delete()
    db.query(User).delete()
    db.add(User(id=1, interests="machine learning, startups"))

    rows = [(topic, text) for topic, texts in POSTS.items() for text in texts]
    vectors = get_embeddings().embed_documents([post_text(t, c) for t, c in rows])
    rng = random.Random(42)
    for (topic, content), vector in zip(rows, vectors, strict=True):
        db.add(
            Post(
                content=content,
                topic=topic,
                quality=rng.random(),
                timestamp=time.time() - rng.randint(0, 10000),
                embedding=vector,
            )
        )
    db.commit()
    db.close()


if __name__ == "__main__":
    seed()
