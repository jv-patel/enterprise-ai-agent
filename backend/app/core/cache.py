"""
In-memory TTL cache.

Process-local by design (no external dependency required to run this
project). Each FastAPI/Uvicorn worker keeps its own cache, which is
sufficient for reducing duplicate calls to slow external APIs (weather, web
search) and for shaving repeated-read latency off dashboard analytics within
a short window. If the app is scaled across multiple processes/instances and
cross-process cache coherence becomes important, swap `TTLCache`'s storage
for Redis behind this same `get`/`set` interface — no call sites change.
"""
import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar

T = TypeVar("T")


@dataclass
class _CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, _CacheEntry] = {}

    def get(self, key: str) -> Any:
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            self._store.pop(key, None)
            return None
        return entry.value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        self._store[key] = _CacheEntry(value=value, expires_at=time.monotonic() + ttl_seconds)

    def invalidate(self, key: str) -> None:
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> None:
        for key in [k for k in self._store if k.startswith(prefix)]:
            self._store.pop(key, None)


_GLOBAL_CACHE = TTLCache()


def get_cache() -> TTLCache:
    return _GLOBAL_CACHE


def cached(ttl_seconds: float, key_prefix: str) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    """Decorator for async functions: caches the return value keyed by
    `key_prefix` + the function's args/kwargs. Only use on functions whose
    arguments are simple, hashable-as-strings values (str, int, None)."""

    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            cache = get_cache()
            key_parts = [key_prefix, *[str(a) for a in args], *[f"{k}={v}" for k, v in sorted(kwargs.items())]]
            cache_key = "|".join(key_parts)

            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper

    return decorator
