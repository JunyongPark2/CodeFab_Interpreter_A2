# ast_nodes.py — Expr / Stmt 노드 클래스 (팀 공용 데이터 구조)

from dataclasses import dataclass
from typing import Any, Optional

from tokens import Token


# ── 모든 Expr의 공통 부모 ──────────────────────────────────────
class Expr:
    pass


@dataclass
class LiteralExpr(Expr):
    value: Any  # float | str | bool | None


@dataclass
class VariableExpr(Expr):
    name: Token  # Token(IDENTIFIER, "변수명")


@dataclass
class AssignExpr(Expr):
    name: Token  # 대입 대상 변수 Token(IDENTIFIER, ...)
    value: Expr  # 대입할 값 표현식


@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: Token  # PLUS / MINUS / STAR / SLASH / GREATER / LESS ...
    right: Expr


@dataclass
class UnaryExpr(Expr):
    operator: Token  # MINUS / BANG
    right: Expr


@dataclass
class GroupingExpr(Expr):
    expression: Expr  # ( 내부 Expr )


@dataclass
class LogicalExpr(Expr):
    left: Expr
    operator: Token  # AND / OR
    right: Expr


# ── 모든 Stmt의 공통 부모 ──────────────────────────────────────
class Stmt:
    pass


@dataclass
class ExpressionStmt(Stmt):
    expression: Expr  # Expr을 Stmt로 감싸는 Wrapper


@dataclass
class PrintStmt(Stmt):
    expression: Expr  # 출력할 표현식


@dataclass
class VarDeclStmt(Stmt):
    name: Token  # 변수 이름 Token(IDENTIFIER, ...)
    initializer: Optional[Expr]  # 초기화 식 (없으면 None)


@dataclass
class BlockStmt(Stmt):
    statements: list[Stmt]  # 블록 내 문장 목록


@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt]  # 없으면 None


@dataclass
class ForStmt(Stmt):
    initializer: Optional[Stmt]  # var i = 0; 또는 None
    condition: Optional[Expr]  # i < 3 또는 None (무한루프)
    increment: Optional[Expr]  # i = i + 1 또는 None
    body: Stmt
