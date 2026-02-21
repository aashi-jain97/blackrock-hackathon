from decimal import Decimal

from app.plugins.base import InvestmentContext, InvestmentPlugin


def calculate_tax(income: Decimal) -> Decimal:
    if income <= Decimal("700000"):
        return Decimal("0")

    tax = Decimal("0")
    slabs = [
        (Decimal("700000"), Decimal("1000000"), Decimal("0.10")),
        (Decimal("1000000"), Decimal("1200000"), Decimal("0.15")),
        (Decimal("1200000"), Decimal("1500000"), Decimal("0.20")),
        (Decimal("1500000"), Decimal("Infinity"), Decimal("0.30")),
    ]

    for lower, upper, rate in slabs:
        if income > lower:
            taxable = min(income, upper) - lower
            if taxable > 0:
                tax += taxable * rate
    return tax


class NpsPlugin(InvestmentPlugin):
    channel_id = "nps"
    annual_rate = Decimal("0.0711")

    def compute_tax_benefit(self, ctx: InvestmentContext) -> Decimal:
        deduction = min(ctx.principal, Decimal("0.10") * ctx.annual_income, Decimal("200000"))
        before = calculate_tax(ctx.annual_income)
        after = calculate_tax(max(Decimal("0"), ctx.annual_income - deduction))
        return before - after
