import uvicorn
from fastapi import Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from crud.posts import create_post, get_all_posts
from db import engine, get_db
from feed.core import generate_feed, get_cached_feed, invalidate_feed, set_cached_feed
from feed.interactions import router as interaction_router
from feed.websocket import manager
from models import Base, User

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(interaction_router)


@app.get("/health")
def health():
    return {"ok": True}


# WebSocket endpoint
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await manager.connect(user_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)


# Feed endpoint with caching
@app.get("/feed/{user_id}")
def get_feed(user_id: int, db: Session = Depends(get_db)):
    cached = get_cached_feed(user_id)
    if cached:
        return {"source": "cache", "data": cached}

    posts = generate_feed(db, user_id)
    feed_data = [{"id": p.id, "topic": p.topic, "content": p.content} for p in posts]
    set_cached_feed(user_id, feed_data)
    return {"source": "computed", "data": feed_data}


@app.post("/notify_new_post")
async def notify_new_post(topic: str, post_id: int, db: Session = Depends(get_db)):
    # Find all users interested in this topic
    users = db.query(User).filter(User.interests.contains(topic)).all()
    for user in users:
        # Invalidate cache
        invalidate_feed(user.id)
        new_feed = generate_feed(db, user.id)
        feed_snippet = [{"id": p.id, "topic": p.topic, "content": p.content} for p in new_feed[:5]]
        await manager.send_feed_update(user.id, {"type": "feed_update", "data": feed_snippet})
    return {"ok": True}


# CRUD endpoints
@app.post("/posts")
async def add_post(content: str, topic: str, quality: float, db: Session = Depends(get_db)):
    # ponytail: sync DB calls inside an async route; move to a worker queue if posting volume grows
    post = create_post(db, content, topic, quality)
    await notify_new_post(topic, post.id, db)
    return {"id": post.id}


@app.get("/posts")
def list_posts(db: Session = Depends(get_db)):
    return get_all_posts(db)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
