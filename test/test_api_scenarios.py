# Test type: API scenario integration test
# Validation: full endpoint behavior across parse/validator/filter/returns/performance with deterministic business outcomes
# Command: pytest -q test/test_api_scenarios.py

def _expenses_payload():
    return {
        "expenses": [
            {"date": "2023-10-12 20:15:00", "amount": 250},
            {"date": "2023-02-28 15:49:00", "amount": 375},
            {"date": "2023-07-01 21:59:00", "amount": 620},
            {"date": "2023-12-17 08:09:00", "amount": 480},
        ]
    }


def _transactions_payload():
    return [
        {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50},
        {"date": "2023-02-28 15:49:00", "amount": 375, "ceiling": 400, "remanent": 25},
        {"date": "2023-07-01 21:59:00", "amount": 620, "ceiling": 700, "remanent": 80},
        {"date": "2023-12-17 08:09:00", "amount": 480, "ceiling": 500, "remanent": 20},
    ]


def _periods_payload():
    return {
        "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
        "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-17 08:09:00"}],
        "k": [
            {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"},
            {"start": "2023-02-28 15:49:00", "end": "2023-12-17 08:09:00"},
        ],
    }


def test_parse_totals_and_rounding(client):
    response = client.post("/blackrock/challenge/v1/transactions:parse", json=_expenses_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["totals"]["totalExpense"] == 1725.0
    assert body["totals"]["totalCeiling"] == 1900.0
    assert body["totals"]["totalRemanent"] == 175.0


def test_validator_duplicates_and_invalid_ceiling(client):
    invalid_tx = {"date": "2023-01-01 00:00:00", "amount": 120, "ceiling": 150, "remanent": 30}
    duplicate_tx = {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50}
    payload = {
        "wage": 50000,
        "transactions": [
            invalid_tx,
            duplicate_tx,
            duplicate_tx,
        ],
    }
    response = client.post("/blackrock/challenge/v1/transactions:validator", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["invalid"]) == 1
    assert body["invalid"][0]["message"] == "ceiling must be a multiple of 100"
    assert len(body["duplicates"]) == 1


def test_filter_applies_q_and_p_rules(client):
    payload = {**_periods_payload(), "transactions": _transactions_payload()}
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["invalid"]) == 0

    tx_by_date = {row["date"]: row for row in body["valid"]}
    assert tx_by_date["2023-10-12 20:15:00"]["remanent"] == 75.0
    assert tx_by_date["2023-07-01 21:59:00"]["remanent"] == 0.0
    assert tx_by_date["2023-12-17 08:09:00"]["remanent"] == 45.0


def test_filter_rejects_out_of_bounds_period(client):
    payload = {
        "q": [],
        "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-31 23:59:59"}],
        "k": [],
        "transactions": _transactions_payload(),
    }
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    assert response.status_code == 422
    assert "outside transaction date bounds" in response.json()["detail"]


def test_returns_nps_and_index_channels(client):
    periods = _periods_payload()
    payload = {
        "age": 29,
        "wage": 50000,
        "inflation": 0.055,
        **periods,
        "transactions": _transactions_payload(),
    }
    nps_response = client.post("/blackrock/challenge/v1/returns:nps", json=payload)
    index_response = client.post("/blackrock/challenge/v1/returns:index", json=payload)

    assert nps_response.status_code == 200
    assert index_response.status_code == 200

    nps = nps_response.json()
    idx = index_response.json()

    assert nps["channel"] == "nps"
    assert idx["channel"] == "index"
    assert len(nps["savingsByDates"]) == 2
    assert len(idx["savingsByDates"]) == 2
    assert idx["savingsByDates"][0]["profits"] > nps["savingsByDates"][0]["profits"]


def test_performance_endpoint_after_requests(client):
    client.post("/blackrock/challenge/v1/transactions:parse", json=_expenses_payload())
    response = client.get("/blackrock/challenge/v1/performance")
    assert response.status_code == 200
    body = response.json()
    assert body["requestsServed"] >= 1
    assert body["threads"] >= 1
    assert "endpointStats" in body


def test_prompt_regression_fixture_amounts(client):
    payload = {
        "age": 29,
        "wage": 50000,
        "inflation": 0.055,
        "kMode": "grouping",
        "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
        "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-17 08:09:00"}],
        "k": [
            {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"},
            {"start": "2023-02-28 15:49:00", "end": "2023-12-17 08:09:00"},
        ],
        "transactions": _transactions_payload(),
    }
    response = client.post("/blackrock/challenge/v1/returns:index", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["savingsByDates"][0]["amount"] == 75.0
    assert body["savingsByDates"][1]["amount"] == 145.0
