from datetime import datetime
from typing import Literal
from typing import List

from pydantic import AliasChoices, BaseModel, Field, field_validator


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def ensure_timestamp(value: str) -> str:
    datetime.strptime(value, TIMESTAMP_FORMAT)
    return value


class ExpenseIn(BaseModel):
    date: str = Field(validation_alias=AliasChoices("date", "timestamp"), serialization_alias="date")
    amount: float = Field(ge=0, lt=500000)

    _valid_date = field_validator("date")(ensure_timestamp)


class Transaction(BaseModel):
    date: str = Field(validation_alias=AliasChoices("date", "timestamp"), serialization_alias="date")
    amount: float = Field(ge=0, lt=500000)
    ceiling: float = Field(ge=0)
    remanent: float = Field(ge=0)

    _valid_date = field_validator("date")(ensure_timestamp)


class ParseRequest(BaseModel):
    expenses: List[ExpenseIn] = Field(default_factory=list)

    @field_validator("expenses")
    @classmethod
    def validate_expenses_size(cls, value: List[ExpenseIn]) -> List[ExpenseIn]:
        if len(value) >= 1_000_000:
            raise ValueError("expenses size must be less than 1,000,000")
        return value


class ParseTotals(BaseModel):
    totalExpense: float
    totalCeiling: float
    totalRemanent: float


class ParseResponse(BaseModel):
    transactions: List[Transaction]
    totals: ParseTotals


class InvalidTransaction(Transaction):
    message: str


class TransactionValidationRequest(BaseModel):
    wage: float = Field(ge=0)
    maxInvest: float | None = Field(default=None, ge=0)
    transactions: List[Transaction] = Field(default_factory=list)

    @field_validator("transactions")
    @classmethod
    def validate_transactions_size(cls, value: List[Transaction]) -> List[Transaction]:
        if len(value) >= 1_000_000:
            raise ValueError("transactions size must be less than 1,000,000")
        return value


class TransactionValidationResponse(BaseModel):
    valid: List[Transaction]
    invalid: List[InvalidTransaction]
    duplicates: List[Transaction]


class FixedPeriod(BaseModel):
    fixed: float = Field(ge=0, lt=500000)
    start: str
    end: str

    _valid_start = field_validator("start")(ensure_timestamp)
    _valid_end = field_validator("end")(ensure_timestamp)


class ExtraPeriod(BaseModel):
    extra: float = Field(ge=0, lt=500000)
    start: str
    end: str

    _valid_start = field_validator("start")(ensure_timestamp)
    _valid_end = field_validator("end")(ensure_timestamp)


class EvalPeriod(BaseModel):
    start: str
    end: str

    _valid_start = field_validator("start")(ensure_timestamp)
    _valid_end = field_validator("end")(ensure_timestamp)


class TemporalFilterRequest(BaseModel):
    q: List[FixedPeriod] = Field(default_factory=list)
    p: List[ExtraPeriod] = Field(default_factory=list)
    k: List[EvalPeriod] = Field(default_factory=list)
    kMode: Literal["grouping", "strict"] = "grouping"
    transactions: List[Transaction] = Field(default_factory=list)

    @field_validator("q", "p", "k", "transactions")
    @classmethod
    def validate_list_sizes(cls, value: list) -> list:
        if len(value) >= 1_000_000:
            raise ValueError("list size must be less than 1,000,000")
        return value


class TemporalTransaction(Transaction):
    pass


class TemporalInvalidTransaction(InvalidTransaction):
    pass


class TemporalFilterResponse(BaseModel):
    valid: List[TemporalTransaction]
    invalid: List[TemporalInvalidTransaction]


class ReturnsRequest(BaseModel):
    age: int = Field(ge=0)
    wage: float = Field(ge=0)
    inflation: float = Field(ge=0)
    q: List[FixedPeriod] = Field(default_factory=list)
    p: List[ExtraPeriod] = Field(default_factory=list)
    k: List[EvalPeriod] = Field(default_factory=list)
    kMode: Literal["grouping", "strict"] = "grouping"
    transactions: List[Transaction] = Field(default_factory=list)

    @field_validator("q", "p", "k", "transactions")
    @classmethod
    def validate_list_sizes(cls, value: list) -> list:
        if len(value) >= 1_000_000:
            raise ValueError("list size must be less than 1,000,000")
        return value


class SavingsByDate(BaseModel):
    start: str
    end: str
    amount: float
    profits: float
    taxBenefit: float


class ReturnsResponse(BaseModel):
    channel: str
    transactionsTotalAmount: float
    transactionsTotalCeiling: float
    savingsByDates: List[SavingsByDate]


class PerformanceResponse(BaseModel):
    time: str
    memory: str
    threads: int
    requestsServed: int
    endpointStats: List[dict] = Field(default_factory=list)
