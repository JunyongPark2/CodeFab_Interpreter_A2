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


@dataclass
class CallExpr(Expr):
    callee: Expr
    paren: Token  # 인자 개수 오류 등에서 라인 번호로 사용
    arguments: list[Expr]


@dataclass
class GetExpr(Expr):
    object: Expr
    name: Token


@dataclass
class SetExpr(Expr):
    object: Expr
    name: Token
    value: Expr


@dataclass
class ThisExpr(Expr):
    keyword: Token


@dataclass
class SuperExpr(Expr):
    keyword: Token
    method: Token


@dataclass
class InstanceOfExpr(Expr):
    object: Expr
    klass: Token


@dataclass
class IndexGetExpr(Expr):
    array: Expr
    bracket: Token  # 에러 라인용
    index: Expr


@dataclass
class IndexSetExpr(Expr):
    array: Expr
    bracket: Token
    index: Expr
    value: Expr


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


@dataclass
class FuncDeclStmt(Stmt):
    name: Token
    params: list[Token]
    body: list[Stmt]  # BlockStmt.statements 재사용


@dataclass
class ReturnStmt(Stmt):
    keyword: Token  # 에러 라인 번호용
    value: Optional[Expr]


@dataclass
class ClassDeclStmt(Stmt):
    name: Token
    superclass: Optional[VariableExpr]
    methods: list[FuncDeclStmt]


@dataclass
class ImportStmt(Stmt):
    path: Token  # STRING 토큰
    alias: Token  # IDENTIFIER
