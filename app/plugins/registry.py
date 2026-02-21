from app.plugins.base import InvestmentPlugin
from app.plugins.index import IndexPlugin
from app.plugins.nps import NpsPlugin


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, InvestmentPlugin] = {
            NpsPlugin.channel_id: NpsPlugin(),
            IndexPlugin.channel_id: IndexPlugin(),
        }

    def get(self, channel_id: str) -> InvestmentPlugin:
        plugin = self._plugins.get(channel_id)
        if not plugin:
            raise ValueError(f"Unsupported investment channel '{channel_id}'")
        return plugin
