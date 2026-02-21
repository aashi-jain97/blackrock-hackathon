# Test type: Judge compatibility integration test
# Validation: maxInvest support, timestamp alias acceptance, and kMode grouping vs strict semantics
# Command: pytest -q test/test_judge_compatibility.py


def test_parse_accepts_timestamp_alias(client):
    payload = {
        "expenses": [
            {"timestamp": "2023-10-12 20:15:00", "amount": 250},
            {"timestamp": "2023-02-28 15:49:00", "amount": 375},
        ]
    }
    response = client.post("/blackrock/challenge/v1/transactions:parse", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["transactions"]) == 2
    assert body["transactions"][0]["date"] == "2023-10-12 20:15:00"


def test_validator_applies_max_invest_rule(client):
    payload = {
        "wage": 50000,
        "maxInvest": 30,
        "transactions": [
            {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50}
        ],
    }
    response = client.post("/blackrock/challenge/v1/transactions:validator", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["invalid"]) == 1
    assert body["invalid"][0]["message"] == "remanent cannot exceed maxInvest"


def test_filter_kmode_grouping_keeps_outside_k_valid(client):
    payload = {
        "q": [],
        "p": [],
        "k": [{"start": "2023-10-10 00:00:00", "end": "2023-10-20 23:59:59"}],
        "kMode": "grouping",
        "transactions": [
            {"date": "2023-10-01 00:00:00", "amount": 100, "ceiling": 100, "remanent": 0},
            {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50},
            {"date": "2023-10-31 23:59:59", "amount": 100, "ceiling": 100, "remanent": 0},
        ],
    }
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["invalid"]) == 0
    assert len(body["valid"]) == 3


def test_filter_kmode_strict_invalidates_outside_k(client):
    payload = {
        "q": [],
        "p": [],
        "k": [{"start": "2023-10-12 20:15:00", "end": "2023-10-12 20:15:00"}],
        "kMode": "strict",
        "transactions": [
            {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50},
            {"date": "2023-10-31 23:59:59", "amount": 100, "ceiling": 100, "remanent": 0},
        ],
    }
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["valid"]) == 1
    assert len(body["invalid"]) == 1
    assert body["invalid"][0]["message"] == "transaction does not fall within any k period"
