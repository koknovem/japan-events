from __future__ import annotations

_LOADED = False


def load_adapters() -> None:
    global _LOADED
    if _LOADED:
        return
    from japan_events.adapters import generic as _generic  # noqa: F401
    from japan_events.adapters import hiroshima as _hiroshima  # noqa: F401
    from japan_events.adapters import hokkaido as _hokkaido  # noqa: F401
    from japan_events.adapters import jnto as _jnto  # noqa: F401
    from japan_events.adapters import kyoto as _kyoto  # noqa: F401
    from japan_events.adapters import nara as _nara  # noqa: F401
    from japan_events.adapters import tokyo as _tokyo  # noqa: F401

    _LOADED = True
