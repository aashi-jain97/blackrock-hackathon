# Save for Your Retirement

FastAPI implementation of the retirement auto-saving challenge with:

- Interface-driven design (plugin registry + repository abstraction)
- SQLite default persistence (migration-ready to Postgres/others)
- Required API endpoints from the problem statement
- Async request handling with FastAPI and threadpool offloading for CPU work
- Security baseline middleware (API key, rate limiting, security headers)

## Tech Stack

- FastAPI
- SQLite (default)
- Pydantic

## Run

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Start server on port 5477:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 5477
```

Optional environment variables:

- `DB_PROVIDER=sqlite|postgres` (default `sqlite`)
- `DB_PATH=/path/to/app.db` (sqlite)
- `POSTGRES_DSN=postgresql://user:pass@host:5432/dbname` (postgres)
- `REQUIRE_API_KEY=true|false` (default `false`)
- `API_KEY=<secret>` (required when `REQUIRE_API_KEY=true`)
- `RATE_LIMIT_PER_MIN=120`

3. Open docs:

```text
http://localhost:5477/docs
```

## Endpoints

- `POST /blackrock/challenge/v1/transactions:parse`
- `POST /blackrock/challenge/v1/transactions:validator`
- `POST /blackrock/challenge/v1/transactions:filter`
- `POST /blackrock/challenge/v1/returns:nps`
- `POST /blackrock/challenge/v1/returns:index`
- `GET /blackrock/challenge/v1/performance`

## Response Contract Notes

- `transactions:filter` returns:
	- `valid`: transactions with updated `remanent` after q/p rule application
	- `invalid`: invalid transactions with `message`
- `returns:nps` and `returns:index` return `savingsByDates` with fields:
	- `start`, `end`, `amount`, `profits`, `taxBenefit`
- Period configuration errors (q/p/k invalid ranges or out-of-bounds windows) return HTTP `422`.
- Parse accepts both `date` and `timestamp` input keys and normalizes to `date` in responses.
- Validator accepts optional `maxInvest` and rejects transactions where remanent exceeds it.
- `kMode` behavior:
	- `grouping` (default): `k` is used for grouping/evaluation only.
	- `strict`: transactions outside every `k` range are marked invalid in filter.

## Performance endpoint

- `/blackrock/challenge/v1/performance` includes:
	- `time`, `memory`, `threads`, `requestsServed`
	- `endpointStats`: endpoint-level counts, avg latency, max latency, and error counts.

## DB Notes

- Default database file: `app.db`
- Override path with environment variable: `DB_PATH`
- Repository abstraction is in `app/repositories/base.py`
- Repository factory is in `app/repositories/factory.py`
- SQLite adapter is in `app/repositories/sqlite_repo.py`
- Postgres adapter is in `app/repositories/postgres_repo.py`

For Postgres mode, set `DB_PROVIDER=postgres` and `POSTGRES_DSN=...`.

## Docker

Build:

```bash
docker build -t blk-hacking-ind-{name-lastname} .
```

Run:

```bash
docker run -d -p 5477:5477 blk-hacking-ind-{name-lastname}
```

Compose:

```bash
docker compose up --build
```

Compose with postgres profile:

```bash
docker compose --profile postgres up --build
```

## Testing and validation

Run tests:

```bash
pytest -q
```

Run smoke checks:

```bash
bash scripts/smoke_test.sh
```

Run lightweight load test:

```bash
python scripts/load_test.py
```

Note: load output includes `throttled` responses when rate-limiter limits are reached.
