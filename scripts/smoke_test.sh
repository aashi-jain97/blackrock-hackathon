#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:5477/blackrock/challenge/v1}"

echo "[1/6] parse"
curl -s -X POST "$BASE_URL/transactions:parse" -H "Content-Type: application/json" -d '{"expenses":[{"date":"2023-10-12 20:15:00","amount":250}]}' | cat
echo

echo "[2/6] validator"
curl -s -X POST "$BASE_URL/transactions:validator" -H "Content-Type: application/json" -d '{"wage":50000,"transactions":[{"date":"2023-10-12 20:15:00","amount":250,"ceiling":300,"remanent":50}]}' | cat
echo

echo "[3/6] filter"
curl -s -X POST "$BASE_URL/transactions:filter" -H "Content-Type: application/json" -d '{"q":[],"p":[],"k":[],"transactions":[{"date":"2023-10-12 20:15:00","amount":250,"ceiling":300,"remanent":50}]}' | cat
echo

echo "[4/6] returns:nps"
curl -s -X POST "$BASE_URL/returns:nps" -H "Content-Type: application/json" -d '{"age":29,"wage":50000,"inflation":0.055,"q":[],"p":[],"k":[{"start":"2023-10-12 20:15:00","end":"2023-10-12 20:15:00"}],"transactions":[{"date":"2023-10-12 20:15:00","amount":250,"ceiling":300,"remanent":50}]}' | cat
echo

echo "[5/6] returns:index"
curl -s -X POST "$BASE_URL/returns:index" -H "Content-Type: application/json" -d '{"age":29,"wage":50000,"inflation":0.055,"q":[],"p":[],"k":[{"start":"2023-10-12 20:15:00","end":"2023-10-12 20:15:00"}],"transactions":[{"date":"2023-10-12 20:15:00","amount":250,"ceiling":300,"remanent":50}]}' | cat
echo

echo "[6/6] performance"
curl -s "$BASE_URL/performance" | cat
echo
