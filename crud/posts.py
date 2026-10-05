import time

from sqlalchemy.orm import Session

from embeddings import get_embeddings, post_text
from models import Post


def create_post(db: Session, content: str, topic: str, quality: float, embeddings=None):
    vector = (embeddings or get_embeddings()).embed_query(post_text(topic, content))
    post = Post(content=content, topic=topic, quality=quality, timestamp=time.time(), embedding=vector)
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


def get_all_posts(db: Session):
    return db.query(Post).all()


def get_post(db: Session, post_id: int):
    return db.query(Post).filter(Post.id == post_id).first()
