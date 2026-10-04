import random
import time

from db import Base, SessionLocal, engine
from models import Post, User

Base.metadata.create_all(bind=engine)
db = SessionLocal()

# Clear existing data
db.query(User).delete()
db.query(Post).delete()

user = User(id=1, interests="tech,ai")
db.add(user)

topics = ["tech", "ai", "finance", "sports"]
for i in range(50):
    post = Post(
        content=f"post {i}",
        topic=random.choice(topics),
        quality=random.random(),
        timestamp=time.time() - random.randint(0, 10000),
    )
    db.add(post)

db.commit()
db.close()
