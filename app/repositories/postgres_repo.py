import os
import threading
from contextlib import contextmanager
from datetime import datetime

import psutil


class PostgresMetricsRepository:
    def __init__(self) -> None:
        self.dsn = os.getenv("POSTGRES_DSN", "")

    @contextmanager
    def _connect(self):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "psycopg is required for DB_PROVIDER=postgres. Install with 'pip install psycopg[binary]'."
            ) from exc

        if not self.dsn:
            raise RuntimeError("POSTGRES_DSN is required for DB_PROVIDER=postgres")

        with psycopg.connect(self.dsn) as conn:
            yield conn

    def initialize(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS request_metrics (
                        id BIGSERIAL PRIMARY KEY,
                        endpoint TEXT NOT NULL,
                        duration_ms DOUBLE PRECISION NOT NULL,
                        status TEXT NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL
                    )
                    """
                )
            conn.commit()

    def save(self, endpoint: str, duration_ms: float, status: str) -> None:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO request_metrics (endpoint, duration_ms, status, created_at)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (endpoint, duration_ms, status, datetime.utcnow()),
                )
            conn.commit()

    def get_performance_snapshot(self) -> dict:
        with self._connect() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(1), AVG(duration_ms) FROM request_metrics")
                row = cursor.fetchone()
                cursor.execute(
                    """
                    SELECT endpoint,
                           COUNT(1) AS total,
                           AVG(duration_ms) AS avg_ms,
                           MAX(duration_ms) AS max_ms,
                           SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) AS error_count
                    FROM request_metrics
                    GROUP BY endpoint
                    ORDER BY endpoint
                    """
                )
                endpoint_rows = cursor.fetchall()

        served = int(row[0] or 0)
        avg_ms = float(row[1] or 0.0)
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / (1024 * 1024)
        endpoint_stats = []
        for endpoint, total, avg_ms, max_ms, error_count in endpoint_rows:
            endpoint_stats.append(
                {
                    "endpoint": endpoint,
                    "count": int(total or 0),
                    "avgMs": round(float(avg_ms or 0.0), 3),
                    "maxMs": round(float(max_ms or 0.0), 3),
                    "errorCount": int(error_count or 0),
                }
            )
        return {
            "time": f"{avg_ms:.3f} ms",
            "memory": f"{memory_mb:.2f} MB",
            "threads": threading.active_count(),
            "requestsServed": served,
            "endpointStats": endpoint_stats,
        }
