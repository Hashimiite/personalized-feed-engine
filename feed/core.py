import time
import json
from sqlalchemy.orm import Session
from models import User, Post, Interaction
from dotenv import load_dotenv
import json
import redis
import json
import os

load_dotenv()

rc = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    decode_responses=True
)


def parse_tags(s):
    return set(s.split(",")) if s else set()

def relevance(user: User, post: Post):
    return len(parse_tags(user.interests) & {post.topic})

def recency(post: Post):
    return 1 / (1 + (time.time() - post.timestamp) / 3600)

def get_click_score(db: Session, post_id: int):
    clicks = db.query(Interaction).filter(
        Interaction.post_id == post_id,
        Interaction.type == "click"
    ).count()
    return clicks * 0.1

def score(db: Session, user: User, post: Post):
    return (
        0.4 * relevance(user, post) +
        0.3 * post.quality +
        0.2 * recency(post) +
        get_click_score(db, post.id)
    )

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

def generate_feed(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return []
    posts = db.query(Post).all()
    ranked = sorted(posts, key=lambda p: score(db, user, p), reverse=True)
    return diversify(ranked)

# Cache helper funcs
def get_cached_feed(user_id: int):
    data = rc.get(f"feed:{user_id}")
    return json.loads(data) if data else None

def set_cached_feed(user_id: int, feed_data: list):
    rc.setex(f"feed:{user_id}", 60, json.dumps(feed_data))

def invalidate_feed(user_id: int):
    rc.delete(f"feed:{user_id}")