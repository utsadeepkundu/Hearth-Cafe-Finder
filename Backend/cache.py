import time
from threading import Lock


class TTLCache:
    """
    Small in-memory cache with per-entry expiry.

    Not distributed or persistent -- it lives in this one process's
    memory -- but that's all a single small backend needs. It cuts
    down drastically on repeat calls to Overpass and Wikimedia for
    the same area, which is where most of the slowness and dropped
    requests were coming from.
    """

    def __init__(self, ttl_seconds: int = 900):
        self.ttl_seconds = ttl_seconds
        self._store = {}
        self._lock = Lock()

    def get(self, key: str):
        with self._lock:
            entry = self._store.get(key)

            if entry is None:
                return None

            value, expires_at = entry

            if time.time() > expires_at:
                del self._store[key]
                return None

            return value

    def set(self, key: str, value):
        with self._lock:
            self._store[key] = (
                value,
                time.time() + self.ttl_seconds,
            )

    @staticmethod
    def make_key(*parts) -> str:
        return "|".join(str(p) for p in parts)
