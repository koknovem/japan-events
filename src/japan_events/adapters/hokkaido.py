from __future__ import annotations

from japan_events.adapters.configured import ConfigurableAdapter
from japan_events.registry import register


@register("hokkaido")
class HokkaidoAdapter(ConfigurableAdapter):
    """HOKKAIDO LOVE! dated listing: index_1_2____1____.html?days={ymd}."""

    name = "hokkaido"
