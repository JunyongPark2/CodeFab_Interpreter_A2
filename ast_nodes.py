"""공통 데이터 구조: Expr / Stmt 노드.

Assembler Unit(Parser) 팀이 완성할 파일이지만, 인터페이스가
CodeFab_Interpreter_Guide.md 5-2, 5-3장에 확정되어 있으므로 Checker 개발/테스트를
위해 동일한 스펙으로 미리 작성한다. 실제 Assembler 코드 합류 시 이 파일을 교체한다.
"""
from dataclasses import dataclass
from typing import Any, Optional

from tokens import Token


# ── Expr ────────────────────────────────────────────────────────
class Expr:
    pass


@dataclass
class LiteralExpr(Expr):
    value: Any


@dataclass
class VariableExpr(Expr):
    name: Token


@dataclass
class AssignExpr(Expr):
    name: Token
    value: Expr


@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: Token
    right: Expr


@dataclass
class UnaryExpr(Expr):
    operator: Token
    right: Expr


@dataclass
class GroupingExpr(Expr):
    expression: Expr


@dataclass
class LogicalExpr(Expr):
    left: Expr
    operator: Token
    right: Expr


# ── Stmt ────────────────────────────────────────────────────────
class Stmt:
    pass


@dataclass
class ExpressionStmt(Stmt):
    expression: Expr


@dataclass
class PrintStmt(Stmt):
    expression: Expr


@dataclass
class VarDeclStmt(Stmt):
    name: Token
    initializer: Optional[Expr]


@dataclass
class BlockStmt(Stmt):
    statements: list[Stmt]


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]


@dataclass
class ForStmt(Stmt):
    initializer: Optional[Stmt]
    condition: Optional[Expr]
    increment: Optional[Expr]
    body: Stmt
