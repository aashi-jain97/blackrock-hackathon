# Test type: Engine unit test
# Validation: temporal rule tie-breaks, additive overlaps, k enforcement, and return horizon calculations
# Command: pytest -q test/test_engine_unit.py

from app.schemas.common import (
    EvalPeriod,
    ExtraPeriod,
    FixedPeriod,
    ParseRequest,
    ReturnsRequest,
    TemporalFilterRequest,
    Transaction,
    TransactionValidationRequest,
)
from app.services.engine import SavingsEngine


def test_q_latest_start_wins_with_same_timestamp_tie_by_order():
    engine = SavingsEngine()
    tx = Transaction(date="2023-07-10 10:00:00", amount=350, ceiling=400, remanent=50)
    tx_min = Transaction(date="2023-07-01 00:00:00", amount=100, ceiling=100, remanent=0)
    tx_max = Transaction(date="2023-07-31 23:59:59", amount=100, ceiling=100, remanent=0)
    payload = TemporalFilterRequest(
        q=[
            FixedPeriod(fixed=10, start="2023-07-01 00:00:00", end="2023-07-31 23:59:59"),
            FixedPeriod(fixed=20, start="2023-07-01 00:00:00", end="2023-07-31 23:59:59"),
            FixedPeriod(fixed=30, start="2023-07-05 00:00:00", end="2023-07-20 23:59:59"),
        ],
        p=[],
        k=[EvalPeriod(start="2023-07-01 00:00:00", end="2023-07-31 23:59:59")],
        transactions=[tx_min, tx, tx_max],
    )
    result = engine.filter_temporal_constraints(payload)
    target = next(row for row in result["valid"] if row["date"] == "2023-07-10 10:00:00")
    assert target["remanent"] == 30.0


def test_p_overlaps_are_summed():
    engine = SavingsEngine()
    tx = Transaction(date="2023-10-12 20:15:00", amount=250, ceiling=300, remanent=50)
    tx_min = Transaction(date="2023-10-01 00:00:00", amount=100, ceiling=100, remanent=0)
    tx_max = Transaction(date="2023-10-31 23:59:59", amount=100, ceiling=100, remanent=0)
    payload = TemporalFilterRequest(
        q=[],
        p=[
            ExtraPeriod(extra=10, start="2023-10-01 00:00:00", end="2023-10-31 23:59:59"),
            ExtraPeriod(extra=5, start="2023-10-10 00:00:00", end="2023-10-20 23:59:59"),
        ],
        k=[EvalPeriod(start="2023-10-01 00:00:00", end="2023-10-31 23:59:59")],
        transactions=[tx_min, tx, tx_max],
    )
    result = engine.filter_temporal_constraints(payload)
    target = next(row for row in result["valid"] if row["date"] == "2023-10-12 20:15:00")
    assert target["remanent"] == 65.0


def test_filter_marks_transaction_invalid_when_not_in_any_k_range():
    engine = SavingsEngine()
    tx_in = Transaction(date="2023-07-01 00:00:00", amount=100, ceiling=100, remanent=0)
    tx_out = Transaction(date="2023-08-01 00:00:00", amount=100, ceiling=100, remanent=0)
    payload = TemporalFilterRequest(
        q=[],
        p=[],
        k=[EvalPeriod(start="2023-07-01 00:00:00", end="2023-07-31 23:59:59")],
        kMode="strict",
        transactions=[tx_in, tx_out],
    )
    result = engine.filter_temporal_constraints(payload)
    assert len(result["valid"]) == 1
    assert len(result["invalid"]) == 1
    assert result["invalid"][0]["message"] == "transaction does not fall within any k period"


def test_parse_rejects_duplicate_dates():
    engine = SavingsEngine()
    payload = ParseRequest(
        expenses=[
            {"date": "2023-01-01 00:00:00", "amount": 100},
            {"date": "2023-01-01 00:00:00", "amount": 200},
        ]
    )
    try:
        engine.parse_transactions(payload)
        assert False, "expected duplicate date validation error"
    except ValueError as exc:
        assert "duplicate transaction date" in str(exc)


def test_validator_rejects_zero_wage_with_positive_remanent():
    engine = SavingsEngine()
    tx = Transaction(date="2023-10-12 20:15:00", amount=250, ceiling=300, remanent=50)
    result = engine.validate_transactions(
        TransactionValidationRequest(wage=0, transactions=[tx])
    )
    assert len(result["invalid"]) == 1
    assert result["invalid"][0]["message"] == "wage must be greater than 0 when remanent exists"


def test_returns_uses_five_year_horizon_for_age_60_or_more():
    engine = SavingsEngine()
    tx = Transaction(date="2023-10-12 20:15:00", amount=250, ceiling=300, remanent=50)
    req = ReturnsRequest(
        age=60,
        wage=50000,
        inflation=0.05,
        q=[],
        p=[],
        k=[EvalPeriod(start="2023-10-12 20:15:00", end="2023-10-12 20:15:00")],
        transactions=[tx],
    )
    response = engine.calculate_returns(req, channel="nps")
    assert response["savingsByDates"][0]["amount"] == 50.0
    assert response["savingsByDates"][0]["profits"] > 0
