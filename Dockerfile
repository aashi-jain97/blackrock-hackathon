# Build command: docker build -t blk-hacking-ind-{name-lastname} .
# OS selection criteria: slim Linux base image chosen for smaller attack surface and startup footprint.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY README.md /app/README.md

EXPOSE 5477

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "5477"]
