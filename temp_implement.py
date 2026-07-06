from dataclasses import dataclass
from typing import Any, Optional


class LangRuntimeError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")

    # ── Expr, Statements 구현시 삭제 ─────────────────────────────────────────────
class Expr:
    pass

@dataclass
class LiteralExpr(Expr):
    value: Any                  # float | str | bool | None

@dataclass
class VariableExpr(Expr):
    name: "Token"               # Token(IDENTIFIER, "변수명")

@dataclass
class AssignExpr(Expr):
    name: "Token"               # 대입 대상 변수 Token(IDENTIFIER, ...)
    value: Expr                 # 대입할 값 표현식

@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: "Token"           # PLUS / MINUS / STAR / SLASH / GREATER / LESS ...
    right: Expr

@dataclass
class UnaryExpr(Expr):
    operator: "Token"           # MINUS / BANG
    right: Expr

@dataclass
class GroupingExpr(Expr):
    expression: Expr            # ( 내부 Expr )

@dataclass
class LogicalExpr(Expr):
    left: Expr
    operator: "Token"           # AND / OR
    right: Expr

class Stmt:
    pass

@dataclass
class ExpressionStmt(Stmt):
    expression: Expr            # Expr을 Stmt로 감싸는 Wrapper

@dataclass
class PrintStmt(Stmt):
    expression: Expr            # 출력할 표현식

@dataclass
class VarDeclStmt(Stmt):
    name: "Token"               # 변수 이름 Token(IDENTIFIER, ...)
    initializer: Optional[Expr] # 초기화 식 (없으면 None)

@dataclass
class BlockStmt(Stmt):
    statements: list[Stmt]      # 블록 내 문장 목록

@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] # 없으면 None

@dataclass
class ForStmt(Stmt):
    initializer: Optional[Stmt]  # var i = 0; 또는 None
    condition: Optional[Expr]    # i < 3 또는 None (무한루프)
    increment: Optional[Expr]    # i = i + 1 또는 None
    body: Stmt

class Environment:
    def __init__(self, parent: Environment | None = None):
        self._values: dict[str, Any] = {}
        self.parent = parent               # 상위 스코프 (None 이면 Global)

    def define(self, name: str, value: Any) -> None:
        """현재 스코프에 변수 선언 (중복 허용 — Checker가 사전 차단)"""
        self._values[name] = value

    def get(self, name: str) -> Any:
        """현재 → 상위 스코프 순으로 변수 탐색"""
        if name in self._values:
            return self._values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise LangRuntimeError(0, f"미정의된 변수 '{name}'")

    def assign(self, name: str, value: Any) -> None:
        """이미 선언된 변수 재할당 (선언된 스코프에 직접 씀)"""
        if name in self._values:
            self._values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise LangRuntimeError(0, f"미정의된 변수 '{name}'")

