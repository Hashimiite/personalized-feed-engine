import json
import os
import time

import numpy as np
import redis
from dotenv import load_dotenv
from sqlalchemy import func
from sqlalchemy.orm import Session

from embeddings import get_embeddings
from models import Interaction, Post, User

load_dotenv()

rc = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)


CANDIDATES = 200  # nearest posts pgvector returns before full scoring
RECENT_CLICKS = 20  # clicked posts that shape a user's profile


def parse_tags(s):
    return {tag.strip() for tag in s.split(",") if tag.strip()} if s else set()


def unit(vector):
    v = np.asarray(vector, dtype=float)
    norm = np.linalg.norm(v)
    return v / norm if norm else v


def user_profile(db: Session, user: User, embeddings=None):
    """Average of the user's stated interests and the posts they clicked most recently, as a unit vector."""
    parts = []
    if user.interests:
        text = f"Interested in {user.interests}"
        parts.append(unit((embeddings or get_embeddings()).embed_query(text)))
    clicked = (
        db.query(Post.embedding)
        .join(Interaction, Interaction.post_id == Post.id)
        .filter(Interaction.user_id == user.id, Interaction.type == "click", Post.embedding.isnot(None))
        .order_by(Interaction.id.desc())
        .limit(RECENT_CLICKS)
        .all()
    )
    if clicked:
        parts.append(unit(np.mean([unit(row[0]) for row in clicked], axis=0)))
    return unit(np.mean(parts, axis=0)) if parts else None


def relevance(profile, post_embedding):
    """Cosine similarity between a profile and a post, clipped to 0 to 1."""
    if profile is None or post_embedding is None:
        return 0.0
    return max(0.0, float(np.dot(profile, unit(post_embedding))))


def recency(post: Post):
    return 1 / (1 + (time.time() - post.timestamp) / 3600)


def click_counts(db: Session, post_ids):
    rows = (
        db.query(Interaction.post_id, func.count())
        .filter(Interaction.post_id.in_(post_ids), Interaction.type == "click")
        .group_by(Interaction.post_id)
        .all()
    )
    return dict(rows)


def score(similarity: float, post: Post, clicks: int):
    return 0.4 * similarity + 0.3 * post.quality + 0.2 * recency(post) + 0.1 * clicks


def diversify(posts, limit=20):
    seen = set()
    result = []
    for p in posts:
        if p.topic not in seen or len(result) < 5:
            result.append(p)
            seen.add(p.topic)
        if len(result) >= limit:
            break
    return result


def generate_feed(db: Session, user_id: int, embeddings=None):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    profile = user_profile(db, user, embeddings)
    query = db.query(Post)
    if profile is not None:
        # pgvector narrows the candidates to the nearest posts before the full score is computed
        query = (
            query.filter(Post.embedding.isnot(None))
            .order_by(Post.embedding.cosine_distance(profile.tolist()))
            .limit(CANDIDATES)
        )
    posts = query.all()
    clicks = click_counts(db, [p.id for p in posts])
    ranked = sorted(
        posts, key=lambda p: score(relevance(profile, p.embedding), p, clicks.get(p.id, 0)), reverse=True
    )
    return diversify(ranked)


def semantic_search(db: Session, text: str, k: int = 5, embeddings=None):
    """The k posts closest in meaning to the text, with their cosine similarity."""
    vector = (embeddings or get_embeddings()).embed_query(text)
    distance = Post.embedding.cosine_distance(vector)
    rows = (
        db.query(Post, distance.label("distance"))
        .filter(Post.embedding.isnot(None))
        .order_by(distance)
        .limit(k)
        .all()
    )
    return [(post, 1 - dist) for post, dist in rows]


# Cache helper funcs
def get_cached_feed(user_id: int):
    data = rc.get(f"feed:{user_id}")
    return json.loads(data) if data else None


def set_cached_feed(user_id: int, feed_data: list):
    rc.set(f"feed:{user_id}", json.dumps(feed_data), ex=60)


def invalidate_feed(user_id: int):
    rc.delete(f"feed:{user_id}")
