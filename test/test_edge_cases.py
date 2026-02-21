# Test type: Domain edge-case unit/integration test
# Validation: strict period constraints, duplicate date parse rejection, and wage/remanent guardrails
# Command: pytest -q test/test_edge_cases.py

def test_parse_duplicate_dates_rejected(client):
    payload = {
        "expenses": [
            {"date": "2023-10-12 20:15:00", "amount": 250},
            {"date": "2023-10-12 20:15:00", "amount": 100},
        ]
    }
    response = client.post("/blackrock/challenge/v1/transactions:parse", json=payload)
    assert response.status_code == 422


def test_invalid_period_returns_422(client):
    payload = {
        "q": [{"fixed": 0, "start": "2023-12-31 23:59:59", "end": "2023-01-01 00:00:00"}],
        "p": [],
        "k": [],
        "transactions": [
            {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50}
        ],
    }
    response = client.post("/blackrock/challenge/v1/transactions:filter", json=payload)
    assert response.status_code == 422


def test_wage_based_validator_rule(client):
    payload = {
        "wage": 40,
        "transactions": [
            {"date": "2023-10-12 20:15:00", "amount": 250, "ceiling": 300, "remanent": 50}
        ],
    }
    response = client.post("/blackrock/challenge/v1/transactions:validator", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert len(body["invalid"]) == 1
    assert body["invalid"][0]["message"] == "remanent cannot exceed wage"
