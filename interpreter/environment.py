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

    def snapshot(self) -> dict[str, Any]:
        """import 기능: 이 Environment(주로 모듈 전용 격리 스코프)에 정의된
        최상위 이름 -> 값 매핑을 복사해서 돌려준다 (LangModule.fields로 옮겨 담는 용도)."""
        return dict(self._values)

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

    def get_at(self, distance: int, name: str) -> Any:
        """정적 바인딩으로 미리 계산된 distance만큼만 올라가 즉시 조회한다 (O(1))."""
        return self._ancestor(distance)._values[name]

    def assign_at(self, distance: int, name: str, value: Any) -> None:
        """정적 바인딩으로 미리 계산된 distance만큼만 올라가 즉시 대입한다 (O(1))."""
        self._ancestor(distance)._values[name] = value

    def _ancestor(self, distance: int) -> "Environment":
        env = self
        for _ in range(distance):
            env = env.parent
        return env
