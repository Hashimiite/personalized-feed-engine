from fastapi import WebSocket
from typing import Dict, Set

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = set()
        self.active_connections[user_id].add(websocket)

    def disconnect(self, user_id: int, websocket: WebSocket):
        self.active_connections.get(user_id, set()).discard(websocket)
        if user_id in self.active_connections and not self.active_connections[user_id]:
            del self.active_connections[user_id]

    async def send_feed_update(self, user_id: int, feed_data: dict):
        for ws in self.active_connections.get(user_id, set()):
            try:
                await ws.send_json(feed_data)
            except:
                pass

manager = ConnectionManager()