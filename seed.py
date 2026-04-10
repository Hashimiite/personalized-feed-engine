from db import SessionLocal, engine, Base
from models import User, Post
import random, time

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
        timestamp=time.time() - random.randint(0, 10000)
    )
    db.add(post)

db.commit()
db.close()