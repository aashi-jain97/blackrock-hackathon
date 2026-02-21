import time
from typing import Callable

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request
from fastapi.concurrency import run_in_threadpool

from app.schemas.common import (
    ParseRequest,
    ParseResponse,
    PerformanceResponse,
    ReturnsRequest,
    ReturnsResponse,
    TemporalFilterRequest,
    TemporalFilterResponse,
    TransactionValidationRequest,
    TransactionValidationResponse,
)
from app.services.engine import SavingsEngine


router = APIRouter(prefix="/blackrock/challenge/v1", tags=["challenge"])


def get_engine() -> SavingsEngine:
    return SavingsEngine()


def get_app(request: Request) -> FastAPI:
    return request.app


async def run_with_metrics(
    app: FastAPI,
    endpoint: str,
    operation: Callable,
) -> dict:
    start = time.perf_counter()
    try:
        response = await run_in_threadpool(operation)
        status = "success"
        return response
    except ValueError as exc:
        status = "error"
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        status = "error"
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        app.state.metrics_repo.save(endpoint=endpoint, duration_ms=duration_ms, status=status)


@router.post("/transactions:parse", response_model=ParseResponse)
async def parse_transactions(
    payload: ParseRequest,
    app: FastAPI = Depends(get_app),
    engine: SavingsEngine = Depends(get_engine),
) -> ParseResponse:
    result = await run_with_metrics(
        app,
        endpoint="transactions:parse",
        operation=lambda: engine.parse_transactions(payload),
    )
    return ParseResponse.model_validate(result)


@router.post("/transactions:validator", response_model=TransactionValidationResponse)
async def validate_transactions(
    payload: TransactionValidationRequest,
    app: FastAPI = Depends(get_app),
    engine: SavingsEngine = Depends(get_engine),
) -> TransactionValidationResponse:
    result = await run_with_metrics(
        app,
        endpoint="transactions:validator",
        operation=lambda: engine.validate_transactions(payload),
    )
    return TransactionValidationResponse.model_validate(result)


@router.post("/transactions:filter", response_model=TemporalFilterResponse)
async def filter_transactions(
    payload: TemporalFilterRequest,
    app: FastAPI = Depends(get_app),
    engine: SavingsEngine = Depends(get_engine),
) -> TemporalFilterResponse:
    result = await run_with_metrics(
        app,
        endpoint="transactions:filter",
        operation=lambda: engine.filter_temporal_constraints(payload),
    )
    return TemporalFilterResponse.model_validate(result)


@router.post("/returns:nps", response_model=ReturnsResponse)
async def calculate_nps_returns(
    payload: ReturnsRequest,
    app: FastAPI = Depends(get_app),
    engine: SavingsEngine = Depends(get_engine),
) -> ReturnsResponse:
    result = await run_with_metrics(
        app,
        endpoint="returns:nps",
        operation=lambda: engine.calculate_returns(payload, channel="nps"),
    )
    return ReturnsResponse.model_validate(result)


@router.post("/returns:index", response_model=ReturnsResponse)
async def calculate_index_returns(
    payload: ReturnsRequest,
    app: FastAPI = Depends(get_app),
    engine: SavingsEngine = Depends(get_engine),
) -> ReturnsResponse:
    result = await run_with_metrics(
        app,
        endpoint="returns:index",
        operation=lambda: engine.calculate_returns(payload, channel="index"),
    )
    return ReturnsResponse.model_validate(result)


@router.get("/performance", response_model=PerformanceResponse)
async def get_performance(
    app: FastAPI = Depends(get_app),
) -> PerformanceResponse:
    try:
        data = app.state.metrics_repo.get_performance_snapshot()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return PerformanceResponse.model_validate(data)
