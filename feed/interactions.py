from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models import Interaction

from .core import invalidate_feed

router = APIRouter(prefix="/interact", tags=["interactions"])


@router.post("/{user_id}/{post_id}")
def interact(user_id: int, post_id: int, db: Session = Depends(get_db)):
    interaction = Interaction(user_id=user_id, post_id=post_id, type="click")
    db.add(interaction)
    db.commit()
    # Invalidate feed cache for this user because click score has changed
    invalidate_feed(user_id)
    return {"message": "interaction recorded"}
