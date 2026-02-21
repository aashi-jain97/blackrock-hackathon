import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib import request
from urllib.error import HTTPError


BASE_URL = "http://127.0.0.1:5477/blackrock/challenge/v1/transactions:parse"


def call_once() -> int:
    payload = {
        "expenses": [
            {"date": "2023-10-12 20:15:00", "amount": 250},
            {"date": "2023-02-28 15:49:00", "amount": 375},
            {"date": "2023-07-01 21:59:00", "amount": 620},
            {"date": "2023-12-17 08:09:00", "amount": 480},
        ]
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(BASE_URL, data=data, method="POST", headers={"Content-Type": "application/json"})
    try:
        with request.urlopen(req, timeout=10) as response:
            return response.status
    except HTTPError as exc:
        return exc.code


def main(total_requests: int = 200, workers: int = 20) -> None:
    started = time.perf_counter()
    statuses = []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(call_once) for _ in range(total_requests)]
        for future in as_completed(futures):
            statuses.append(future.result())

    elapsed = time.perf_counter() - started
    ok = sum(1 for status in statuses if status == 200)
    throttled = sum(1 for status in statuses if status == 429)
    errors = len(statuses) - ok - throttled
    print(f"total_requests={total_requests}")
    print(f"workers={workers}")
    print(f"ok={ok}")
    print(f"throttled={throttled}")
    print(f"errors={errors}")
    print(f"elapsed_sec={elapsed:.3f}")
    print(f"throughput_rps={total_requests / elapsed:.2f}")


if __name__ == "__main__":
    main()
