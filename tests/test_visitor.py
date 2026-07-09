"""Expr/Stmt.accept()의 더블 디스패치 자체를 검증한다.

test_checker.py / test_executor.py가 "언어 기능이 맞게 동작하는가"를 보는 반면,
여기서는 Visitor 패턴 리팩터링(dict 기반 handler -> accept() 더블 디스패치)이
실제로 준 이득 두 가지를 직접 확인한다:

1. 새 연산(visitor)을 ast_nodes.py를 건드리지 않고도 추가할 수 있다.
2. 새 노드 타입에 대응하는 visit_ 메서드가 없으면, 예전 dict.get() 방식처럼
   조용히 무시되지 않고 즉시 NotImplementedError로 드러난다.
"""

from dataclasses import dataclass

import pytest

from interpreter.ast_nodes import BinaryExpr, Expr, LiteralExpr, Stmt
from interpreter.checker import Checker
from interpreter.executor import Executor
from interpreter.tokens import Token, TokenType


def plus_token() -> Token:
    return Token(TokenType.PLUS, "+")


# ── 1. accept()는 노드 타입에 맞는 visit_ 메서드를 정확히 찾아 호출한다 ──


def test_accept_dispatches_by_node_type_to_matching_visit_method():
    calls = []

    class SpyVisitor:
        def visit_LiteralExpr(self, expr):
            calls.append(("literal", expr.value))
            return "literal-result"

        def visit_BinaryExpr(self, expr):
            calls.append(("binary", expr.operator.type))
            return "binary-result"

    literal_result = LiteralExpr(1.0).accept(SpyVisitor())
    binary_result = BinaryExpr(LiteralExpr(1.0), plus_token(), LiteralExpr(2.0)).accept(
        SpyVisitor()
    )

    assert literal_result == "literal-result"
    assert binary_result == "binary-result"
    assert calls == [("literal", 1.0), ("binary", TokenType.PLUS)]


# ── 2. Checker/Executor를 전혀 건드리지 않고도 새 연산(visitor)을 추가할 수 있다 ──


def test_new_visitor_can_be_added_without_touching_ast_nodes_or_checker_or_executor():
    # 예: AST를 사람이 읽는 중위표기 문자열로 바꿔주는 완전히 새로운 연산.
    # ast_nodes.py 쪽 코드는 한 줄도 안 바뀌었는데 그냥 동작해야 한다 —
    # dict 기반 handler였다면 이 visitor도 자기만의 dict를 처음부터 채워야 했다.
    class ReprVisitor:
        def visit_LiteralExpr(self, expr):
            return repr(expr.value)

        def visit_BinaryExpr(self, expr):
            left = expr.left.accept(self)
            right = expr.right.accept(self)
            return f"({left} {expr.operator.origin} {right})"

    expr = BinaryExpr(LiteralExpr(1.0), plus_token(), LiteralExpr(2.0))
    assert expr.accept(ReprVisitor()) == "(1.0 + 2.0)"


# ── 3. 같은 노드라도 어떤 visitor에게 넘기냐에 따라 다른 연산이 실행된다 ──


def test_same_binary_expr_is_folded_by_checker_but_computed_by_executor():
    # Checker는 상수 폴딩을 위해 LiteralExpr(3.0)으로 "접은 트리"를 돌려주고,
    # Executor는 같은 트리를 "실행"해서 숫자 3.0을 직접 계산한다.
    # 노드 타입(BinaryExpr)은 같지만 visitor 타입(Checker/Executor)에 따라
    # 완전히 다른 visit_BinaryExpr가 실행된다는 것이 더블 디스패치의 핵심이다.
    expr = BinaryExpr(LiteralExpr(1.0), plus_token(), LiteralExpr(2.0))

    folded = Checker([])._check_expr(expr)
    assert isinstance(folded, LiteralExpr)
    assert folded.value == 3.0

    assert Executor([])._eval(expr) == 3.0


# ── 4. 새 노드 타입에 handler가 없으면 조용히 무시되지 않고 즉시 에러가 난다 ──


def test_checker_raises_immediately_for_expr_type_it_has_no_visit_method_for():
    @dataclass
    class UnsupportedExpr(Expr):
        pass

    with pytest.raises(NotImplementedError, match="visit_UnsupportedExpr"):
        UnsupportedExpr().accept(Checker([]))


def test_executor_raises_immediately_for_stmt_type_it_has_no_visit_method_for():
    @dataclass
    class UnsupportedStmt(Stmt):
        pass

    with pytest.raises(NotImplementedError, match="visit_UnsupportedStmt"):
        UnsupportedStmt().accept(Executor([]))
