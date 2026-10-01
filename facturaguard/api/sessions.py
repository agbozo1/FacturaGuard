"""In-memory sessions with expiry. Nothing is written to disk (synthetic data, no retention)."""

import secrets
import threading
import time

TTL_SECONDS = 60 * 60
MAX_SESSIONS = 500


class SessionStore:
    def __init__(self, ttl: int = TTL_SECONDS, max_sessions: int = MAX_SESSIONS):
        self.ttl, self.max = ttl, max_sessions
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _evict(self) -> None:
        now = time.time()
        for sid in [s for s, v in self._data.items() if now - v["_touched"] > self.ttl]:
            del self._data[sid]
        while len(self._data) >= self.max:
            oldest = min(self._data, key=lambda s: self._data[s]["_touched"])
            del self._data[oldest]

    def create(self, **values) -> str:
        with self._lock:
            self._evict()
            sid = secrets.token_urlsafe(16)
            self._data[sid] = {**values, "_touched": time.time()}
            return sid

    def get(self, sid: str) -> dict | None:
        with self._lock:
            s = self._data.get(sid)
            if s is None or time.time() - s["_touched"] > self.ttl:
                self._data.pop(sid, None)
                return None
            s["_touched"] = time.time()
            return s
