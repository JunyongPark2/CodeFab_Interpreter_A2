from dataclasses import dataclass
from typing import Any, Optional

from .tokens import Token


# ── Expr ─────────────────────────────────────────────────────
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


# ── 정적배열 기능 ────────────────────────────────────────────
@dataclass
class ArrayExpr(Expr):
    size: Expr
    keyword: Token


@dataclass
class IndexExpr(Expr):
    array: Expr
    index: Expr
    bracket: Token


@dataclass
class IndexAssignExpr(Expr):
    array: Expr
    index: Expr
    value: Expr
    bracket: Token


# ── Stmt ─────────────────────────────────────────────────────
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