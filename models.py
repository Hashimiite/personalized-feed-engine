from pgvector.sqlalchemy import VECTOR
from sqlalchemy import Column, Float, ForeignKey, Integer, String

from db import Base
from embeddings import DIM


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    interests = Column(String)


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True)
    content = Column(String)
    topic = Column(String)
    quality = Column(Float)
    timestamp = Column(Float)
    embedding = Column(VECTOR(DIM))


class Interaction(Base):
    __tablename__ = "interactions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    post_id = Column(Integer, ForeignKey("posts.id"))
    type = Column(String)
