# --- Place these imports near the top of api/main.py ---
from prometheus_client import make_asgi_app
from api.observability import RequestIdMiddleware, StructuredLoggingMiddleware, MetricsMiddleware


app.add_middleware(RequestIdMiddleware)
app.add_middleware(StructuredLoggingMiddleware)
app.add_middleware(MetricsMiddleware)


metrics_asgi_app = make_asgi_app()
app.mount("/metrics", metrics_asgi_app)