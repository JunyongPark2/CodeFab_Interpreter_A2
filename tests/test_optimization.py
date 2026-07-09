"""실행 전 최적화(정적 바인딩 / 상수 폴딩)를 Test Double(스파이)로 검증한다.

Assembler -> Checker -> Executor 전체 파이프라인을 CodeFabInterpreter로 돌려서,
"최적화가 실제로 런타임 동작을 바꿨는지"를 실제 호출 횟수로 확인한다.
"""

from interpreter.codefab import CodeFabInterpreter
from interpreter.environment import Environment
from interpreter.executor import Executor
from interpreter.tokens import TokenType


def test_resolved_local_variable_never_calls_dynamic_get(monkeypatch, capsys):
    # { var a = 1; { var b = a + 1; print b; } }
    # a의 참조는 정적 바인딩으로 distance가 계산되므로 Executor는 get_at()만 써야 하고
    # Environment.get()(동적 조회)은 한 번도 호출되면 안 된다.
    calls = {"get": 0}
    original_get = Environment.get

    def spy_get(self, name, line=0):
        calls["get"] += 1
        return original_get(self, name, line)

    monkeypatch.setattr(Environment, "get", spy_get)

    source = "{ var a = 1; { var b = a + 1; print b; } }"
    CodeFabInterpreter().run(source)

    assert capsys.readouterr().out == "2\n"
    assert calls["get"] == 0


def test_top_level_global_variable_still_uses_dynamic_get(monkeypatch, capsys):
    # 대조군: 전역 변수는 정적 바인딩 대상이 아니므로 여전히 get()이 호출돼야 한다.
    # (위 스파이 테스트가 "우연히 get이 항상 0번 호출되는" 구현이 아님을 보증한다.)
    calls = {"get": 0}
    original_get = Environment.get

    def spy_get(self, name, line=0):
        calls["get"] += 1
        return original_get(self, name, line)

    monkeypatch.setattr(Environment, "get", spy_get)

    CodeFabInterpreter().run("var g = 1; print g;")

    assert capsys.readouterr().out == "1\n"
    assert calls["get"] == 1


def test_folded_constant_expression_is_never_recomputed_in_loop(monkeypatch, capsys):
    # for (var i = 0; i < 3; i = i + 1) { print (2 * 3); }
    # (2 * 3)은 Checker 단계에서 이미 LiteralExpr(6.0)으로 접혀야 하므로, 루프를 3번
    # 돌아도 Executor.visit_BinaryExpr가 STAR 연산자로 호출되는 일이 없어야 한다.
    calls = {"STAR": 0, "LESS": 0}
    original_eval_binary = Executor.visit_BinaryExpr

    def spy_eval_binary(self, expr):
        op_name = expr.operator.type.name
        if op_name in calls:
            calls[op_name] += 1
        return original_eval_binary(self, expr)

    monkeypatch.setattr(Executor, "visit_BinaryExpr", spy_eval_binary)

    source = "for (var i = 0; i < 3; i = i + 1) { print (2 * 3); }"
    CodeFabInterpreter().run(source)

    assert capsys.readouterr().out == "6\n6\n6\n"
    assert calls["STAR"] == 0  # 상수 폴딩으로 곱셈 자체가 사라졌다
    # i < 3 은 변수가 껴 있어 폴딩 대상이 아니므로 조건 검사마다(참 3번 + 마지막 거짓 1번) 재계산된다
    assert calls["LESS"] == 4


def test_modulo_constant_expression_in_loop_is_never_recomputed(monkeypatch, capsys):
    calls = {"MODULO": 0}
    original_eval_binary = Executor.visit_BinaryExpr

    def spy_eval_binary(self, expr):
        if expr.operator.type == TokenType.MODULO:
            calls["MODULO"] += 1
        return original_eval_binary(self, expr)

    monkeypatch.setattr(Executor, "visit_BinaryExpr", spy_eval_binary)

    source = """
var total = 0;
for (var i = 0; i < 3; i = i + 1) {
    total = total + (1 - 2 * 3 * 4 * 5 / 6 + 7 + 8 + 9) % 1000 % 30;
}
print total;
"""
    CodeFabInterpreter().run(source)

    assert capsys.readouterr().out == "15\n"
    assert calls["MODULO"] == 0


def test_this_reference_never_calls_dynamic_get(monkeypatch, capsys):
    # Class A { setX(x) { This.x = x; } f() { print This.x; } }
    # init()은 생성자 종료 후 인스턴스를 돌려주려고 런타임(CodeFabFunction.call)이
    # 항상 closure에서 직접 This를 한 번 꺼내므로(AST의 ThisExpr와 무관, 항상
    # distance 0이라 사실상 O(1)) 여기서는 일부러 init 없는 클래스로 검증해서
    # ThisExpr 정적 바인딩 자체만 순수하게 확인한다.
    calls = {"get_this": 0}
    original_get = Environment.get

    def spy_get(self, name, line=0):
        if name == "This":
            calls["get_this"] += 1
        return original_get(self, name, line)

    monkeypatch.setattr(Environment, "get", spy_get)

    source = """
Class A {
    setX(x) { This.x = x; }
    f() { print This.x; }
}
var a = A();
a.setX(5);
a.f();
"""
    CodeFabInterpreter().run(source)

    assert capsys.readouterr().out == "5\n"
    assert calls["get_this"] == 0
