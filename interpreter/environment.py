from __future__ import annotations

from typing import Any

from .errors import LangRuntimeError


class Environment:
    def __init__(self, parent: "Environment | None" = None):
        self._values: dict[str, Any] = {}
        self.parent = parent

    @property
    def names(self) -> set[str]:
        return set(self._values.keys())

    def define(self, name: str, value: Any) -> None:
        self._values[name] = value

    def get(self, name: str, line: int = 0) -> Any:
        if name in self._values:
            return self._values[name]
        if self.parent is not None:
            return self.parent.get(name, line)
        raise LangRuntimeError(line, f"미정의된 변수 '{name}'")

    def assign(self, name: str, value: Any, line: int = 0) -> None:
        if name in self._values:
            self._values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value, line)
            return
        raise LangRuntimeError(line, f"미정의된 변수 '{name}'")
