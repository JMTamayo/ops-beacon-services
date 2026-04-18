from __future__ import annotations

from typing import Callable


class FredOps:
    def __init__(self) -> None:
        self._execute_fn: Callable | None = None
        self._storage_fn: Callable | None = None

    def execute(self, fn: Callable) -> Callable:
        if self._execute_fn is not None:
            raise RuntimeError(
                f"execute function already registered: '{self._execute_fn.__name__}'. "
                "Only one @app.execute is allowed per FredOps instance."
            )
        self._execute_fn = fn
        return fn

    def get_execute(self) -> Callable:
        if self._execute_fn is None:
            raise RuntimeError(
                "No execute function registered. "
                "Did you forget to decorate your function with @app.execute?"
            )
        return self._execute_fn

    def storage(self, fn: Callable) -> Callable:
        if self._storage_fn is not None:
            raise RuntimeError(
                f"storage function already registered: '{self._storage_fn.__name__}'. "
                "Only one @app.storage is allowed per FredOps instance."
            )
        self._storage_fn = fn
        return fn

    def get_storage(self) -> Callable | None:
        return self._storage_fn
