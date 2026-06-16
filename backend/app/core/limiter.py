"""
core/limiter.py — shared slowapi Limiter instance.

Keyed by client IP. Uses in-memory storage (single process). For a
multi-worker production deployment, point storage_uri at Redis, e.g.:

    Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
