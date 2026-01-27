import asyncio


class BroadcastManager:
    """Manages SSE subscriptions and broadcasts events to connected clients."""

    def __init__(self) -> None:
        self.subscribers: set[asyncio.Queue] = set()

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to the broadcast stream."""
        q: asyncio.Queue = asyncio.Queue()
        self.subscribers.add(q)
        return q

    async def unsubscribe(self, q: asyncio.Queue) -> None:
        """Unsubscribe from the broadcast stream."""
        if q in self.subscribers:
            self.subscribers.remove(q)

    async def broadcast(self, event_type: str, data: str) -> None:
        """Broadcast an event to all subscribers."""
        if not self.subscribers:
            return

        message = {"event": event_type, "data": data}

        for q in list(self.subscribers):
            try:
                q.put_nowait(message)
            except Exception:
                pass
