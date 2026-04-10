from sqlalchemy.orm import Session
from models import Post
import time

def create_post(db: Session, content: str, topic: str, quality: float):
    post = Post(content=content, topic=topic, quality=quality, timestamp=time.time())
    db.add(post)
    db.commit()
    db.refresh(post)
    return post

def get_all_posts(db: Session):
    return db.query(Post).all()

def get_post(db: Session, post_id: int):
    return db.query(Post).filter(Post.id == post_id).first()