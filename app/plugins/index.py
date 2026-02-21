from decimal import Decimal

from app.plugins.base import InvestmentPlugin


class IndexPlugin(InvestmentPlugin):
    channel_id = "index"
    annual_rate = Decimal("0.1449")
