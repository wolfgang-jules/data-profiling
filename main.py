"""Dispatcher entrypoint for selecting profiling engine(s)."""

from __future__ import annotations

import importlib
from typing import Callable, cast


def _get_runner(engine: str) -> Callable[[], None]:
    """Load selected engine entrypoint dynamically from a simple string."""
    normalized = engine.strip().lower()
    if normalized == "dataprep":
        module_name = "main_dataprep"
    elif normalized == "ydata":
        module_name = "main_ydata"
    else:
        raise ValueError("Invalid engine. Use 'dataprep' or 'ydata'.")

    module = importlib.import_module(module_name)
    main_entrypoint = getattr(module, "main", None)
    if not callable(main_entrypoint):
        raise AttributeError(f"Module '{module_name}' must expose a callable 'main'.")
    return cast(Callable[[], None], main_entrypoint)


if __name__ == "__main__":
    ENGINE = "ydata"  # dataprep | ydata
    runner = _get_runner(ENGINE)
    runner()
