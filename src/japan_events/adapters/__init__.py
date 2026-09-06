from __future__ import annotations

import importlib
import pkgutil

_LOADED = False


def load_adapters() -> None:
    """Import built-in + sites/* adapters so @register side effects run."""
    global _LOADED
    if _LOADED:
        return
    from japan_events.adapters import generic as _generic  # noqa: F401
    from japan_events.adapters import configured as _configured  # noqa: F401

    # Legacy top-level adapters (kept for import compatibility)
    for mod in ("hiroshima", "hokkaido", "jnto", "kyoto", "nara", "tokyo"):
        try:
            importlib.import_module(f"japan_events.adapters.{mod}")
        except ImportError:
            pass

    # Preferred location for custom Python adapters
    try:
        import japan_events.adapters.sites as sites_pkg

        for info in pkgutil.iter_modules(sites_pkg.__path__, sites_pkg.__name__ + "."):
            if info.name.rsplit(".", 1)[-1].startswith("_"):
                continue
            importlib.import_module(info.name)
    except ImportError:
        pass

    _LOADED = True
