import json
import logging
import time
import uuid
from contextvars import ContextVar
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge

# Configure the logger used across the API application
logger = logging.getLogger("m11.api")

# --- Metric Declarations ---
requests_total = Counter(
    "requests_total",
    "Total number of HTTP requests processed",
    labelnames=["path", "status"]
)

request_latency_seconds = Histogram(
    "request_latency_seconds",
    "HTTP request latency in seconds",
    labelnames=["path"]
)

inflight_requests = Gauge(
    "inflight_requests",
    "Number of HTTP requests currently in flight"
)

# ContextVar to maintain request isolated scope across async calls
request_id_var: ContextVar[str] = ContextVar("request_id")


# --- Middlewares ---

class RequestIdMiddleware(BaseHTTPMiddleware):
    """Outermost Middleware: Assigns a unique tracking hex UUID to every request."""
    async def dispatch(self, request: Request, call_next):
        req_id = uuid.uuid4().hex
        token = request_id_var.set(req_id)
        
        response: Response = await call_next(request)
        
        # Set response header (requests are read-only at this lifecycle stage)
        response.headers["X-Request-ID"] = req_id
        request_id_var.reset(token)
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middle Middleware: Times requests and emits a standardized JSON log string."""
    async def dispatch(self, request: Request, call_next):
        start_time = time.perf_counter()
        response: Response = await call_next(request)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        
        req_id = request_id_var.get("")
        
        # Explicit json.dumps formatting as the starter lacks a structured formatter
        log_data = {
            "request_id": req_id,
            "path": request.url.path,
            "status": response.status_code,
            "latency_ms": elapsed_ms
        }
        
        logger.info(json.dumps(log_data))
        return response


class MetricsMiddleware(BaseHTTPMiddleware):
    """Innermost Middleware: Records core Prometheus instrumentation statistics."""
    async def dispatch(self, request: Request, call_next):
        inflight_requests.inc()
        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
            return response
        finally:
            elapsed = time.perf_counter() - start_time
            inflight_requests.dec()
            
            path = request.url.path
            status = str(response.status_code)
            
            requests_total.labels(path=path, status=status).inc()
            request_latency_seconds.labels(path=path).observe(elapsed)