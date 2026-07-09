# tests/test_runtime.py — interpreter/runtime.py 자체에 대한 유닛 테스트.
#
# CodeFabFunction/CodeFabClass/CodeFabInstance/CodeFabModule은 대부분 Executor
# 통합 테스트(test_executor.py, test_executor_function.py, test_codefab.py)를
# 통해 간접적으로 커버되지만, 여기서는 runtime.py의 저수준 계약(추상 메서드,
# __str__, Checker를 거치지 않았을 때의 방어적 동작)만 직접 검증한다.
import pytest

from interpreter.ast_nodes import FuncDeclStmt, LiteralExpr, ReturnStmt
from interpreter.environment import Environment
from interpreter.executor import Executor
from interpreter.runtime import (
    CodeFabCallable,
    CodeFabClass,
    CodeFabFunction,
    CodeFabModule,
)
from interpreter.tokens import TokenType
from tests.helpers import name_tok, tok

# ── CodeFabCallable: 추상 계약 ──────────────────────────────────


def test_callable_base_arity_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        CodeFabCallable().arity()


def test_callable_base_call_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        CodeFabCallable().call(executor=None, arguments=[])


# ── __str__ 표현 ─────────────────────────────────────────────────


def test_function_str_representation():
    decl = FuncDeclStmt(name=name_tok("add"), params=[], body=[])
    func = CodeFabFunction(decl, Environment())
    assert str(func) == "<function add>"


def test_class_str_representation():
    klass = CodeFabClass("Robot", superclass=None, methods={})
    assert str(klass) == "<class Robot>"


def test_module_str_representation():
    module = CodeFabModule("sum")
    assert str(module) == "<module sum>"


# ── init()의 return 처리: Checker를 거치지 않았을 때의 방어적 동작 ──────
#
# Checker가 init() 안의 return을 전면 금지하므로, 정상적인 파이프라인에서는
# is_initializer=True인 함수가 return으로 빠져나오는 경로를 절대 안 탄다.
# 하지만 CodeFabFunction.call()은 Checker와 독립적인 계약이라, 누군가 AST를
# 직접 구성해 Executor만 단독으로 호출하는 경우(이 테스트처럼)에는 여전히
# "return 값과 무관하게 항상 This를 돌려준다"는 규칙을 지켜야 한다.
def test_initializer_call_ignores_return_value_and_returns_this():
    decl = FuncDeclStmt(
        name=name_tok("init"),
        params=[],
        body=[ReturnStmt(keyword=tok(TokenType.RETURN), value=LiteralExpr(999.0))],
    )
    closure = Environment()
    instance_sentinel = object()
    closure.define("This", instance_sentinel)

    func = CodeFabFunction(decl, closure, is_initializer=True)
    result = func.call(Executor([]), [])

    assert result is instance_sentinel
