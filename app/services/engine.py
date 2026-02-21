from bisect import bisect_left, bisect_right
from datetime import datetime
from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
import heapq

from app.plugins.base import InvestmentContext
from app.plugins.registry import PluginRegistry
from app.schemas.common import (
    ParseRequest,
    ReturnsRequest,
    TemporalFilterRequest,
    Transaction,
    TransactionValidationRequest,
)

TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def to_dt(value: str) -> datetime:
    return datetime.strptime(value, TIMESTAMP_FORMAT)


def to_decimal(value: float | int | Decimal) -> Decimal:
    return Decimal(str(value))


def to_money_float(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


class SavingsEngine:
    def __init__(self) -> None:
        self.registry = PluginRegistry()

    def parse_transactions(self, payload: ParseRequest) -> dict:
        transactions: list[dict] = []
        total_amount = Decimal("0")
        total_ceiling = Decimal("0")
        total_remanent = Decimal("0")
        seen_dates: set[str] = set()

        for expense in payload.expenses:
            if expense.date in seen_dates:
                raise ValueError("duplicate transaction date found in expenses")
            seen_dates.add(expense.date)

            amount = to_decimal(expense.amount)
            rounded = (amount / Decimal("100")).to_integral_value(rounding=ROUND_CEILING) * Decimal("100")
            remanent = rounded - amount
            transaction = {
                "date": expense.date,
                "amount": to_money_float(amount),
                "ceiling": to_money_float(rounded),
                "remanent": to_money_float(remanent),
            }
            transactions.append(transaction)
            total_amount += amount
            total_ceiling += rounded
            total_remanent += remanent

        return {
            "transactions": transactions,
            "totals": {
                "totalExpense": to_money_float(total_amount),
                "totalCeiling": to_money_float(total_ceiling),
                "totalRemanent": to_money_float(total_remanent),
            },
        }

    def validate_transactions(self, payload: TransactionValidationRequest) -> dict:
        valid: list[dict] = []
        invalid: list[dict] = []
        duplicates: list[dict] = []
        seen_dates: set[str] = set()
        wage = to_decimal(payload.wage)
        max_invest = to_decimal(payload.maxInvest) if payload.maxInvest is not None else None

        for tx in payload.transactions:
            tx_dict = tx.model_dump()
            if tx.date in seen_dates:
                duplicates.append(tx_dict)
                continue
            seen_dates.add(tx.date)

            error = self._validate_transaction(tx, wage=wage, max_invest=max_invest)
            if error:
                invalid.append({**tx_dict, "message": error})
            else:
                valid.append(tx_dict)

        return {"valid": valid, "invalid": invalid, "duplicates": duplicates}

    def filter_temporal_constraints(self, payload: TemporalFilterRequest) -> dict:
        invalid: list[tuple[int, dict]] = []
        valid: list[tuple[int, dict]] = []
        tx_dates = [to_dt(tx.date) for tx in payload.transactions]
        min_tx_date = min(tx_dates) if tx_dates else None
        max_tx_date = max(tx_dates) if tx_dates else None

        self._validate_periods(payload.q, "q", min_tx_date, max_tx_date)
        self._validate_periods(payload.p, "p", min_tx_date, max_tx_date)
        self._validate_periods(payload.k, "k", min_tx_date, max_tx_date)

        sorted_tx = sorted(enumerate(payload.transactions), key=lambda item: to_dt(item[1].date))

        q_rules = self._prepare_q_rules(payload.q)
        q_ptr = 0
        q_heap: list[tuple[float, int, datetime, Decimal]] = []

        p_rules = sorted(
            [(to_dt(rule.start), to_dt(rule.end), to_decimal(rule.extra)) for rule in payload.p],
            key=lambda item: item[0],
        )
        p_ptr = 0
        p_end_heap: list[tuple[datetime, Decimal]] = []
        active_extra = Decimal("0")

        k_rules = sorted(
            [(to_dt(rule.start), to_dt(rule.end)) for rule in payload.k],
            key=lambda item: item[0],
        )
        k_ptr = 0
        k_end_heap: list[datetime] = []
        active_k_count = 0

        for original_idx, tx in sorted_tx:
            message = self._validate_transaction(tx)
            if message:
                invalid.append((original_idx, {**tx.model_dump(), "message": message}))
                continue

            tx_dt = to_dt(tx.date)

            while q_ptr < len(q_rules) and q_rules[q_ptr][0] <= tx_dt:
                start_dt, list_index, end_dt, fixed = q_rules[q_ptr]
                heapq.heappush(q_heap, (-start_dt.timestamp(), list_index, end_dt, fixed))
                q_ptr += 1

            while q_heap and q_heap[0][2] < tx_dt:
                heapq.heappop(q_heap)

            while p_ptr < len(p_rules) and p_rules[p_ptr][0] <= tx_dt:
                _, end_dt, extra = p_rules[p_ptr]
                heapq.heappush(p_end_heap, (end_dt, extra))
                active_extra += extra
                p_ptr += 1

            while p_end_heap and p_end_heap[0][0] < tx_dt:
                _, extra = heapq.heappop(p_end_heap)
                active_extra -= extra

            while k_ptr < len(k_rules) and k_rules[k_ptr][0] <= tx_dt:
                _, end_dt = k_rules[k_ptr]
                heapq.heappush(k_end_heap, end_dt)
                active_k_count += 1
                k_ptr += 1

            while k_end_heap and k_end_heap[0] < tx_dt:
                heapq.heappop(k_end_heap)
                active_k_count -= 1

            adjusted = to_decimal(tx.remanent)
            if q_heap:
                adjusted = q_heap[0][3]
            adjusted += active_extra
            adjusted = max(Decimal("0"), adjusted)

            in_k_range = (not payload.k) or (active_k_count > 0)

            if payload.kMode == "strict" and (not in_k_range):
                invalid.append(
                    (original_idx,
                    {
                        **tx.model_dump(),
                        "message": "transaction does not fall within any k period",
                    })
                )
                continue

            tx_data = tx.model_dump()
            tx_data["remanent"] = to_money_float(adjusted)
            valid.append((original_idx, tx_data))

        valid_sorted = [item[1] for item in sorted(valid, key=lambda item: item[0])]
        invalid_sorted = [item[1] for item in sorted(invalid, key=lambda item: item[0])]
        return {"valid": valid_sorted, "invalid": invalid_sorted}

    def calculate_returns(self, payload: ReturnsRequest, channel: str) -> dict:
        temporal = self.filter_temporal_constraints(
            TemporalFilterRequest(
                q=payload.q,
                p=payload.p,
                k=payload.k,
                kMode=payload.kMode,
                transactions=payload.transactions,
            )
        )
        valid_transactions = temporal["valid"]
        plugin = self.registry.get(channel)

        years = (60 - payload.age) if payload.age < 60 else 5
        annual_income = to_decimal(payload.wage) * Decimal("12")
        inflation = to_decimal(payload.inflation)
        savings_by_dates: list[dict] = []
        sorted_valid = sorted(valid_transactions, key=lambda tx: to_dt(tx["date"]))
        sorted_dates = [to_dt(tx["date"]) for tx in sorted_valid]
        prefix: list[Decimal] = [Decimal("0")]
        for tx in sorted_valid:
            prefix.append(prefix[-1] + to_decimal(tx["remanent"]))

        for period in payload.k:
            start = to_dt(period.start)
            end = to_dt(period.end)
            if start > end:
                continue

            left = bisect_left(sorted_dates, start)
            right = bisect_right(sorted_dates, end)
            amount = prefix[right] - prefix[left]

            ctx = InvestmentContext(
                principal=amount,
                years=years,
                annual_income=annual_income,
                inflation=inflation,
            )
            nominal = plugin.compute_nominal_return(ctx)
            real = nominal / ((Decimal("1") + inflation) ** years) if years > 0 else nominal
            tax_benefit = plugin.compute_tax_benefit(ctx)

            savings_by_dates.append(
                {
                    "start": period.start,
                    "end": period.end,
                    "amount": to_money_float(amount),
                    "profits": to_money_float(real - amount),
                    "taxBenefit": to_money_float(tax_benefit),
                }
            )

        return {
            "channel": channel,
            "transactionsTotalAmount": to_money_float(
                sum((to_decimal(tx["amount"]) for tx in valid_transactions), Decimal("0"))
            ),
            "transactionsTotalCeiling": to_money_float(
                sum((to_decimal(tx["ceiling"]) for tx in valid_transactions), Decimal("0"))
            ),
            "savingsByDates": savings_by_dates,
        }

    def _validate_transaction(
        self,
        tx: Transaction,
        wage: Decimal | None = None,
        max_invest: Decimal | None = None,
    ) -> str | None:
        amount = to_decimal(tx.amount)
        ceiling = to_decimal(tx.ceiling)
        remanent = to_decimal(tx.remanent)

        if amount < 0 or ceiling < 0 or remanent < 0:
            return "amount, ceiling and remanent must be non-negative"
        if amount >= Decimal("500000"):
            return "amount must be less than 500000"
        if ceiling < amount:
            return "ceiling cannot be less than amount"
        if (ceiling % Decimal("100")) != 0:
            return "ceiling must be a multiple of 100"
        if (ceiling - amount).quantize(Decimal("0.01")) != remanent.quantize(Decimal("0.01")):
            return "remanent must equal ceiling - amount"
        if wage is not None:
            if wage <= 0 and remanent > 0:
                return "wage must be greater than 0 when remanent exists"
            if remanent > wage:
                return "remanent cannot exceed wage"
        if max_invest is not None and remanent > max_invest:
            return "remanent cannot exceed maxInvest"
        return None

    def _prepare_q_rules(self, q_rules) -> list[tuple[datetime, int, datetime, Decimal]]:
        prepared = []
        for index, rule in enumerate(q_rules):
            prepared.append((to_dt(rule.start), index, to_dt(rule.end), to_decimal(rule.fixed)))
        prepared.sort(key=lambda item: (item[0], item[1]))
        return prepared

    def _validate_periods(self, periods, label: str, min_tx_date: datetime | None, max_tx_date: datetime | None) -> None:
        for idx, period in enumerate(periods):
            start_dt = to_dt(period.start)
            end_dt = to_dt(period.end)
            if start_dt > end_dt:
                raise ValueError(f"{label}[{idx}] has start > end")
            if min_tx_date and (start_dt < min_tx_date or end_dt > max_tx_date):
                raise ValueError(f"{label}[{idx}] is outside transaction date bounds")
