from dataclasses import dataclass
from decimal import Decimal


@dataclass
class InvestmentContext:
    principal: Decimal
    years: int
    annual_income: Decimal
    inflation: Decimal


class InvestmentPlugin:
    channel_id: str
    annual_rate: Decimal

    def compute_nominal_return(self, ctx: InvestmentContext) -> Decimal:
        return ctx.principal * ((Decimal("1") + self.annual_rate) ** ctx.years)

    def compute_tax_benefit(self, ctx: InvestmentContext) -> Decimal:
        return Decimal("0")
