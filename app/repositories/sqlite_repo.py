import os
import sqlite3
import threading
from datetime import datetime

import psutil


class SqliteMetricsRepository:
    def __init__(self, db_path: str | None = None) -> None:
        self.db_path = db_path or os.getenv("DB_PATH", "app.db")

    def initialize(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS request_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    endpoint TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save(self, endpoint: str, duration_ms: float, status: str) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO request_metrics (endpoint, duration_ms, status, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (endpoint, duration_ms, status, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def get_performance_snapshot(self) -> dict:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(1), AVG(duration_ms) FROM request_metrics")
            row = cursor.fetchone()
            endpoint_rows = conn.execute(
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
            ).fetchall()

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
