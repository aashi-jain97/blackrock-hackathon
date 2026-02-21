import os
import threading
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Cache-Control"] = "no-store"
        return response


class ApiKeyMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.enabled = os.getenv("REQUIRE_API_KEY", "false").strip().lower() == "true"
        self.api_key = os.getenv("API_KEY", "")
        self.exempt_paths = {
            "/docs",
            "/redoc",
            "/openapi.json",
        }

    async def dispatch(self, request: Request, call_next):
        if not self.enabled or request.url.path in self.exempt_paths:
            return await call_next(request)

        provided = request.headers.get("x-api-key", "")
        if not self.api_key or provided != self.api_key:
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})
        return await call_next(request)


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.limit = int(os.getenv("RATE_LIMIT_PER_MIN", "120"))
        self.window_seconds = 60
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    async def dispatch(self, request: Request, call_next):
        client = request.client.host if request.client else "unknown"
        now = time.time()

        with self.lock:
            bucket = self.hits[client]
            while bucket and (now - bucket[0]) > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.limit:
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
            bucket.append(now)

        return await call_next(request)
