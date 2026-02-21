import os

from app.repositories.postgres_repo import PostgresMetricsRepository
from app.repositories.sqlite_repo import SqliteMetricsRepository


def create_metrics_repository():
    provider = os.getenv("DB_PROVIDER", "sqlite").strip().lower()

    if provider == "sqlite":
        return SqliteMetricsRepository()

    if provider == "postgres":
        return PostgresMetricsRepository()

    raise ValueError(f"Unsupported DB provider '{provider}'. Use 'sqlite' or 'postgres'.")
