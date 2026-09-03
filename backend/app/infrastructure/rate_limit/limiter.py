from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

# In-memory storage by default: no extra infrastructure needed for a single
# API process or for tests. Swap storage_uri="redis://..." (REDIS_URL is
# already configured in Settings) once the API runs as more than one worker,
# so limits are shared across processes instead of counted per-worker.
limiter = Limiter(key_func=get_remote_address)
