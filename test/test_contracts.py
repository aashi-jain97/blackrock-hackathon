# Test type: API contract and integration test
# Validation: endpoint response shapes and required fields for parse/filter/returns/performance
# Command: pytest -q test/test_contracts.py

def _sample_transactions():
    return [
        {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50},
        {"date": "2023-02-28 15:49:00", "amount": 375, "ceiling": 400, "remanent": 25},
        {"date": "2023-07-01 21:59:00", "amount": 620, "ceiling": 700, "remanent": 80},
        {"date": "2023-12-17 08:09:00", "amount": 480, "ceiling": 500, "remanent": 20},
    ]


def _periods():
    return {
        "q": [{"fixed": 0, "start": "2023-07-01 00:00:00", "end": "2023-07-31 23:59:59"}],
        "p": [{"extra": 25, "start": "2023-10-01 08:00:00", "end": "2023-12-17 08:09:00"}],
        "k": [
            {"start": "2023-03-01 00:00:00", "end": "2023-11-30 23:59:59"},
            {"start": "2023-02-28 15:49:00", "end": "2023-12-17 08:09:00"},
        ],
    }


def test_parse_contract(client):
    response = client.post(
        "/blackrock/challenge/v1/transactions:parse",
        json={"expenses": [{"date": "2023-10-12 20:15:00", "amount": 250}]},
    )
    assert response.status_code == 200
    body = response.json()
    assert "transactions" in body
    assert "totals" in body


def test_filter_contract(client):
    periods = _periods()
    payload = {**periods, "transactions": _sample_transactions()}
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"valid", "invalid"}
    if body["valid"]:
        sample = body["valid"][0]
        assert set(sample.keys()) == {"date", "amount", "ceiling", "remanent"}


def test_returns_contract_index(client):
    periods = _periods()
    payload = {
        "age": 29,
        "wage": 50000,
        "inflation": 0.055,
        **periods,
        "transactions": _sample_transactions(),
    }
    response = client.post("/blackrock/challenge/v1/returns:index", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "channel",
        "transactionsTotalAmount",
        "transactionsTotalCeiling",
        "savingsByDates",
    }
    for row in body["savingsByDates"]:
        assert set(row.keys()) == {"start", "end", "amount", "profits", "taxBenefit"}


def test_performance_contract(client):
    response = client.get("/blackrock/challenge/v1/performance")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {"time", "memory", "threads", "requestsServed", "endpointStats"}
