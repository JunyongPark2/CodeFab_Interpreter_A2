from dataclasses import dataclass
from typing import Any, Optional

from .tokens import Token


# ── Expr ─────────────────────────────────────────────────────
class Expr:
    def accept(self, visitor):
        """visitor에서 이 노드 타입에 대응하는 visit_<클래스명> 메서드를 찾아
        더블 디스패치로 호출한다. 해당 메서드가 없으면 visitor가 이 노드 타입을
        아직 처리할 준비가 안 된 것이므로, 조용히 넘어가지 않고 즉시 에러를 낸다
        (dict.get() 기반 디스패치가 누락된 타입을 조용히 무시하던 문제를 방지)."""
        method_name = f"visit_{type(self).__name__}"
        method = getattr(visitor, method_name, None)
        if method is None:
            raise NotImplementedError(
                f"{type(visitor).__name__}에 '{method_name}' 메서드가 없습니다."
            )
        return method(self)


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


# ── 정적배열 기능: 배열 생성 (인덱스 읽기/쓰기는 위의 IndexGetExpr/IndexSetExpr 사용) ──
@dataclass
class ArrayExpr(Expr):
    size: Expr
    keyword: Token


# ── Stmt ─────────────────────────────────────────────────────
class Stmt:
    def accept(self, visitor):
        """Expr.accept()와 동일한 더블 디스패치 규칙(visit_<클래스명>)을 따른다."""
        method_name = f"visit_{type(self).__name__}"
        method = getattr(visitor, method_name, None)
        if method is None:
            raise NotImplementedError(
                f"{type(visitor).__name__}에 '{method_name}' 메서드가 없습니다."
            )
        return method(self)


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
