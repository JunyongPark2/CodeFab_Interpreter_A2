# test_executor_function.py — Function 기능에 대한 Executor 유닛 테스트 (TDD)
#
# Parser는 이미 Func/return/CallExpr를 파싱하도록 구현되어 있지만, 이 파일은
# 기존 test_executor.py와 동일하게 Assembler(Parser)를 거치지 않고 AST를
# 직접 구성해서 Executor만 단위로 검증한다.
#
# dld.md 5-1 Function — Executor 런타임 설계 기준:
#   - 함수는 "값"이다 (LangFunction, 정의 시점 환경을 closure로 캡처)
#   - CallExpr 평가: callee 평가 -> 호출 가능 여부 확인 -> 인자 개수 확인
#     -> 새 Environment(parent=closure) -> 파라미터 define -> 본문 실행
#   - return은 예외(ReturnSignal)로 구현. 값 없는 return / return 없이 끝까지
#     실행되면 결과는 nil.
#   - 런타임 에러: 함수가 아닌 대상 호출, 인자 개수 불일치.
import pytest

from interpreter.ast_nodes import (
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ExpressionStmt,
    ForStmt,
    FuncDeclStmt,
    IfStmt,
    LiteralExpr,
    PrintStmt,
    ReturnStmt,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from interpreter.errors import CodeFabRuntimeError
from interpreter.executor import Executor
from interpreter.tokens import Token, TokenType


def tok(type_, origin="", value=None, line=1, col=1):
    return Token(type=type_, origin=origin, value=value, line=line, col=col)


def name_tok(name, line=1):
    return tok(TokenType.IDENTIFIER, origin=name, line=line)


def run(stmts):
    Executor(stmts).execute()


def make_func(name, params, body_stmts, line=1):
    return FuncDeclStmt(
        name=name_tok(name, line=line),
        params=[name_tok(p, line=line) for p in params],
        body=body_stmts,
    )


def make_call(callee_name, arguments, line=1):
    return CallExpr(
        callee=VariableExpr(name=name_tok(callee_name, line=line)),
        paren=tok(TokenType.RIGHT_PAREN, line=line),
        arguments=arguments,
    )


def make_return(value=None, line=1):
    return ReturnStmt(keyword=tok(TokenType.RETURN, line=line), value=value)


def var(name, line=1):
    return VariableExpr(name_tok(name, line=line))


def lit(value):
    return LiteralExpr(value)


def bin_(left, op_type, right):
    return BinaryExpr(left=left, operator=tok(op_type), right=right)


# ── 함수는 값을 계산해서 돌려준다 ──────────────────────────────────
def test_call_returns_computed_value(capsys):
    add = make_func(
        "add",
        ["a", "b"],
        [
            make_return(
                BinaryExpr(
                    left=VariableExpr(name_tok("a")),
                    operator=tok(TokenType.PLUS),
                    right=VariableExpr(name_tok("b")),
                )
            )
        ],
    )
    run([add, PrintStmt(expression=make_call("add", [LiteralExpr(1.0), LiteralExpr(2.0)]))])
    assert capsys.readouterr().out == "3\n"


def test_function_declaration_itself_prints_nothing(capsys):
    run([make_func("noop", [], [])])
    assert capsys.readouterr().out == ""


# ── return 값 유무에 따른 결과 ──────────────────────────────────────
def test_function_without_return_yields_nil(capsys):
    run([make_func("noop", [], []), PrintStmt(expression=make_call("noop", []))])
    assert capsys.readouterr().out == "nil\n"


def test_bare_return_yields_nil(capsys):
    early = make_func("early", [], [make_return(None)])
    run([early, PrintStmt(expression=make_call("early", []))])
    assert capsys.readouterr().out == "nil\n"


def test_return_skips_remaining_statements(capsys):
    f = make_func(
        "f",
        [],
        [
            make_return(LiteralExpr(1.0)),
            PrintStmt(expression=LiteralExpr(value="unreachable")),
        ],
    )
    run([f, PrintStmt(expression=make_call("f", []))])
    assert capsys.readouterr().out == "1\n"


def test_return_exits_nested_for_and_if(capsys):
    # Func first_even(limit) {
    #   for (var i = 0; i < limit; i = i + 1) {
    #     if (i == 2) { return i; }
    #   }
    #   return -1;
    # }
    body = [
        ForStmt(
            initializer=VarDeclStmt(name=name_tok("i"), initializer=LiteralExpr(0.0)),
            condition=BinaryExpr(
                left=VariableExpr(name_tok("i")),
                operator=tok(TokenType.LESS),
                right=VariableExpr(name_tok("limit")),
            ),
            increment=AssignExpr(
                name=name_tok("i"),
                value=BinaryExpr(
                    left=VariableExpr(name_tok("i")),
                    operator=tok(TokenType.PLUS),
                    right=LiteralExpr(1.0),
                ),
            ),
            body=BlockStmt(
                [
                    IfStmt(
                        condition=BinaryExpr(
                            left=VariableExpr(name_tok("i")),
                            operator=tok(TokenType.EQUAL_EQUAL),
                            right=LiteralExpr(2.0),
                        ),
                        then_branch=BlockStmt([make_return(VariableExpr(name_tok("i")))]),
                        else_branch=None,
                    )
                ]
            ),
        ),
        make_return(LiteralExpr(-1.0)),
    ]
    run(
        [
            make_func("first_even", ["limit"], body),
            PrintStmt(expression=make_call("first_even", [LiteralExpr(10.0)])),
        ]
    )
    assert capsys.readouterr().out == "2\n"


# ── 재귀 호출 (정의 시점 환경을 closure로 캡처) ───────────────────────
def test_recursive_call_via_closure(capsys):
    # Func fact(n) {
    #   if (n <= 1) { return 1; }
    #   return n * fact(n - 1);
    # }
    body = [
        IfStmt(
            condition=BinaryExpr(
                left=VariableExpr(name_tok("n")),
                operator=tok(TokenType.LESS_EQUAL),
                right=LiteralExpr(1.0),
            ),
            then_branch=BlockStmt([make_return(LiteralExpr(1.0))]),
            else_branch=None,
        ),
        make_return(
            BinaryExpr(
                left=VariableExpr(name_tok("n")),
                operator=tok(TokenType.STAR),
                right=make_call(
                    "fact",
                    [
                        BinaryExpr(
                            left=VariableExpr(name_tok("n")),
                            operator=tok(TokenType.MINUS),
                            right=LiteralExpr(1.0),
                        )
                    ],
                ),
            )
        ),
    ]
    run([make_func("fact", ["n"], body), PrintStmt(expression=make_call("fact", [LiteralExpr(5.0)]))])
    assert capsys.readouterr().out == "120\n"


# ── 파라미터/호출 스코프 격리 ────────────────────────────────────────
def test_parameters_do_not_leak_into_outer_scope(capsys):
    square = make_func(
        "square",
        ["x"],
        [
            make_return(
                BinaryExpr(
                    left=VariableExpr(name_tok("x")),
                    operator=tok(TokenType.STAR),
                    right=VariableExpr(name_tok("x")),
                )
            )
        ],
    )
    run(
        [
            square,
            VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(100.0)),
            PrintStmt(expression=make_call("square", [LiteralExpr(5.0)])),
            PrintStmt(expression=VariableExpr(name_tok("x"))),
        ]
    )
    assert capsys.readouterr().out == "25\n100\n"


def test_each_call_gets_a_fresh_environment(capsys):
    identity = make_func("identity", ["x"], [make_return(VariableExpr(name_tok("x")))])
    run(
        [
            identity,
            PrintStmt(expression=make_call("identity", [LiteralExpr(1.0)])),
            PrintStmt(expression=make_call("identity", [LiteralExpr(2.0)])),
        ]
    )
    assert capsys.readouterr().out == "1\n2\n"


# ── 함수는 값이다 ───────────────────────────────────────────────────
def test_function_is_a_value_can_be_assigned_and_called(capsys):
    add = make_func(
        "add",
        ["a", "b"],
        [
            make_return(
                BinaryExpr(
                    left=VariableExpr(name_tok("a")),
                    operator=tok(TokenType.PLUS),
                    right=VariableExpr(name_tok("b")),
                )
            )
        ],
    )
    run(
        [
            add,
            VarDeclStmt(name=name_tok("f"), initializer=VariableExpr(name_tok("add"))),
            PrintStmt(
                expression=CallExpr(
                    callee=VariableExpr(name_tok("f")),
                    paren=tok(TokenType.RIGHT_PAREN),
                    arguments=[LiteralExpr(2.0), LiteralExpr(3.0)],
                )
            ),
        ]
    )
    assert capsys.readouterr().out == "5\n"


def test_function_can_call_another_function(capsys):
    square = make_func(
        "square",
        ["x"],
        [
            make_return(
                BinaryExpr(
                    left=VariableExpr(name_tok("x")),
                    operator=tok(TokenType.STAR),
                    right=VariableExpr(name_tok("x")),
                )
            )
        ],
    )
    sum_of_squares = make_func(
        "sum_of_squares",
        ["a", "b"],
        [
            make_return(
                BinaryExpr(
                    left=make_call("square", [VariableExpr(name_tok("a"))]),
                    operator=tok(TokenType.PLUS),
                    right=make_call("square", [VariableExpr(name_tok("b"))]),
                )
            )
        ],
    )
    run(
        [
            square,
            sum_of_squares,
            PrintStmt(expression=make_call("sum_of_squares", [LiteralExpr(3.0), LiteralExpr(4.0)])),
        ]
    )
    assert capsys.readouterr().out == "25\n"


# ── 런타임 에러 ──────────────────────────────────────────────────────
def test_calling_non_function_value_raises():
    line = 3
    stmts = [
        VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr("hi")),
        ExpressionStmt(
            expression=CallExpr(
                callee=VariableExpr(name_tok("x", line=line)),
                paren=tok(TokenType.RIGHT_PAREN, line=line),
                arguments=[],
            )
        ),
    ]
    with pytest.raises(
            CodeFabRuntimeError, match=rf"\[{line}번째줄\] 함수가 아닌 대상을 호출했습니다\."
    ):
        run(stmts)


def test_call_with_too_few_arguments_raises():
    line = 4
    add = make_func(
        "add",
        ["a", "b"],
        [
            make_return(
                BinaryExpr(
                    left=VariableExpr(name_tok("a")),
                    operator=tok(TokenType.PLUS),
                    right=VariableExpr(name_tok("b")),
                )
            )
        ],
    )
    call = ExpressionStmt(
        expression=CallExpr(
            callee=VariableExpr(name_tok("add", line=line)),
            paren=tok(TokenType.RIGHT_PAREN, line=line),
            arguments=[LiteralExpr(1.0)],
        )
    )
    with pytest.raises(
            CodeFabRuntimeError, match=rf"\[{line}번째줄\] 인자 개수가 일치하지 않습니다\."
    ):
        run([add, call])


def test_call_with_too_many_arguments_raises():
    line = 4
    add = make_func(
        "add",
        ["a", "b"],
        [
            make_return(
                BinaryExpr(
                    left=VariableExpr(name_tok("a")),
                    operator=tok(TokenType.PLUS),
                    right=VariableExpr(name_tok("b")),
                )
            )
        ],
    )
    call = ExpressionStmt(
        expression=CallExpr(
            callee=VariableExpr(name_tok("add", line=line)),
            paren=tok(TokenType.RIGHT_PAREN, line=line),
            arguments=[LiteralExpr(1.0), LiteralExpr(2.0), LiteralExpr(3.0)],
        )
    )
    with pytest.raises(
            CodeFabRuntimeError, match=rf"\[{line}번째줄\] 인자 개수가 일치하지 않습니다\."
    ):
        run([add, call])


# ── 추가: 더 복잡한 시나리오 ──────────────────────────────────────────

def test_mutual_recursion_is_even_is_odd(capsys):
    is_even = make_func(
        "is_even",
        ["n"],
        [
            IfStmt(
                condition=bin_(var("n"), TokenType.EQUAL_EQUAL, lit(0.0)),
                then_branch=BlockStmt([make_return(lit(True))]),
                else_branch=None,
            ),
            make_return(make_call("is_odd", [bin_(var("n"), TokenType.MINUS, lit(1.0))])),
        ],
    )
    is_odd = make_func(
        "is_odd",
        ["n"],
        [
            IfStmt(
                condition=bin_(var("n"), TokenType.EQUAL_EQUAL, lit(0.0)),
                then_branch=BlockStmt([make_return(lit(False))]),
                else_branch=None,
            ),
            make_return(make_call("is_even", [bin_(var("n"), TokenType.MINUS, lit(1.0))])),
        ],
    )
    run(
        [
            is_even,
            is_odd,
            PrintStmt(expression=make_call("is_even", [lit(10.0)])),
            PrintStmt(expression=make_call("is_odd", [lit(10.0)])),
        ]
    )
    assert capsys.readouterr().out == "true\nfalse\n"


def test_fibonacci_recursive(capsys):
    fib_body = [
        IfStmt(
            condition=bin_(var("n"), TokenType.LESS_EQUAL, lit(1.0)),
            then_branch=BlockStmt([make_return(var("n"))]),
            else_branch=None,
        ),
        make_return(
            bin_(
                make_call("fib", [bin_(var("n"), TokenType.MINUS, lit(1.0))]),
                TokenType.PLUS,
                make_call("fib", [bin_(var("n"), TokenType.MINUS, lit(2.0))]),
            )
        ),
    ]
    run([make_func("fib", ["n"], fib_body), PrintStmt(expression=make_call("fib", [lit(10.0)]))])
    assert capsys.readouterr().out == "55\n"


def test_function_returning_boolean(capsys):
    is_positive = make_func(
        "is_positive", ["n"], [make_return(bin_(var("n"), TokenType.GREATER, lit(0.0)))]
    )
    run(
        [
            is_positive,
            PrintStmt(expression=make_call("is_positive", [lit(5.0)])),
            PrintStmt(expression=make_call("is_positive", [lit(-5.0)])),
        ]
    )
    assert capsys.readouterr().out == "true\nfalse\n"


def test_function_returning_concatenated_string(capsys):
    greet_body = [
        make_return(bin_(bin_(lit("Hello, "), TokenType.PLUS, var("name")), TokenType.PLUS, lit("!")))
    ]
    run(
        [
            make_func("greet", ["name"], greet_body),
            PrintStmt(expression=make_call("greet", [lit("CodeFab")])),
        ]
    )
    assert capsys.readouterr().out == "Hello, CodeFab!\n"


def test_function_declared_inside_braced_block_is_scoped_to_block():
    line = 4
    stmts = [
        IfStmt(
            condition=lit(True),
            then_branch=BlockStmt([make_func("f", [], [make_return(lit(1.0))])]),
            else_branch=None,
        ),
        ExpressionStmt(expression=make_call("f", [], line=line)),
    ]
    with pytest.raises(CodeFabRuntimeError, match=rf"\[{line}번째줄\] 미정의된 변수 'f'"):
        run(stmts)


def test_function_declared_as_bare_if_body_leaks_into_outer_scope(capsys):
    # 중괄호 없는 단일 문장 본문은 새 스코프를 만들지 않으므로, if 밖에서도 보여야 한다.
    stmts = [
        IfStmt(
            condition=lit(True),
            then_branch=make_func("f", [], [make_return(lit(1.0))]),
            else_branch=None,
        ),
        PrintStmt(expression=make_call("f", [])),
    ]
    run(stmts)
    assert capsys.readouterr().out == "1\n"


def test_parameter_shadows_outer_function_name(capsys):
    add = make_func("add", ["a", "b"], [make_return(bin_(var("a"), TokenType.PLUS, var("b")))])
    # trick의 파라미터 이름이 전역 함수 add와 같아서, 함수 본문 안에서는
    # 전역 함수가 아니라 파라미터 값을 가리켜야 한다.
    trick = make_func("trick", ["add"], [make_return(var("add"))])
    run([add, trick, PrintStmt(expression=make_call("trick", [lit(99.0)]))])
    assert capsys.readouterr().out == "99\n"


def test_function_can_mutate_outer_variable(capsys):
    increment = make_func(
        "increment",
        [],
        [
            ExpressionStmt(
                expression=AssignExpr(
                    name=name_tok("counter"),
                    value=bin_(var("counter"), TokenType.PLUS, lit(1.0)),
                )
            )
        ],
    )
    run(
        [
            VarDeclStmt(name=name_tok("counter"), initializer=lit(0.0)),
            increment,
            ExpressionStmt(expression=make_call("increment", [])),
            ExpressionStmt(expression=make_call("increment", [])),
            ExpressionStmt(expression=make_call("increment", [])),
            PrintStmt(expression=var("counter")),
        ]
    )
    assert capsys.readouterr().out == "3\n"


def test_call_with_expression_arguments(capsys):
    square = make_func("square", ["x"], [make_return(bin_(var("x"), TokenType.STAR, var("x")))])
    run(
        [
            square,
            PrintStmt(expression=make_call("square", [bin_(lit(2.0), TokenType.PLUS, lit(3.0))])),
        ]
    )
    assert capsys.readouterr().out == "25\n"


def test_nested_call_as_argument(capsys):
    inc = make_func("inc", ["x"], [make_return(bin_(var("x"), TokenType.PLUS, lit(1.0)))])
    double = make_func("double", ["x"], [make_return(bin_(var("x"), TokenType.STAR, lit(2.0)))])
    run(
        [
            inc,
            double,
            PrintStmt(expression=make_call("double", [make_call("inc", [lit(3.0)])])),
        ]
    )
    assert capsys.readouterr().out == "8\n"


def test_function_called_repeatedly_in_loop(capsys):
    square = make_func("square", ["x"], [make_return(bin_(var("x"), TokenType.STAR, var("x")))])
    loop = ForStmt(
        initializer=VarDeclStmt(name=name_tok("i"), initializer=lit(0.0)),
        condition=bin_(var("i"), TokenType.LESS, lit(4.0)),
        increment=AssignExpr(name=name_tok("i"), value=bin_(var("i"), TokenType.PLUS, lit(1.0))),
        body=PrintStmt(expression=make_call("square", [var("i")])),
    )
    run([square, loop])
    assert capsys.readouterr().out == "0\n1\n4\n9\n"


def test_higher_order_function_receives_function_as_argument(capsys):
    square = make_func("square", ["x"], [make_return(bin_(var("x"), TokenType.STAR, var("x")))])
    apply_twice_body = [
        make_return(
            CallExpr(
                callee=var("f"),
                paren=tok(TokenType.RIGHT_PAREN),
                arguments=[
                    CallExpr(callee=var("f"), paren=tok(TokenType.RIGHT_PAREN), arguments=[var("x")])
                ],
            )
        )
    ]
    apply_twice = make_func("apply_twice", ["f", "x"], apply_twice_body)
    run(
        [
            square,
            apply_twice,
            PrintStmt(expression=make_call("apply_twice", [var("square"), lit(2.0)])),
        ]
    )
    assert capsys.readouterr().out == "16\n"


def test_closure_captures_enclosing_function_parameter(capsys):
    # Func make_adder(x) { Func adder(y) { return x + y; } return adder; }
    adder = make_func("adder", ["y"], [make_return(bin_(var("x"), TokenType.PLUS, var("y")))])
    make_adder = make_func("make_adder", ["x"], [adder, make_return(var("adder"))])
    run(
        [
            make_adder,
            VarDeclStmt(name=name_tok("add5"), initializer=make_call("make_adder", [lit(5.0)])),
            PrintStmt(
                expression=CallExpr(
                    callee=var("add5"), paren=tok(TokenType.RIGHT_PAREN), arguments=[lit(3.0)]
                )
            ),
        ]
    )
    assert capsys.readouterr().out == "8\n"


def test_closures_from_separate_calls_are_independent(capsys):
    adder = make_func("adder", ["y"], [make_return(bin_(var("x"), TokenType.PLUS, var("y")))])
    make_adder = make_func("make_adder", ["x"], [adder, make_return(var("adder"))])
    run(
        [
            make_adder,
            VarDeclStmt(name=name_tok("add5"), initializer=make_call("make_adder", [lit(5.0)])),
            VarDeclStmt(name=name_tok("add10"), initializer=make_call("make_adder", [lit(10.0)])),
            PrintStmt(
                expression=CallExpr(
                    callee=var("add5"), paren=tok(TokenType.RIGHT_PAREN), arguments=[lit(1.0)]
                )
            ),
            PrintStmt(
                expression=CallExpr(
                    callee=var("add10"), paren=tok(TokenType.RIGHT_PAREN), arguments=[lit(1.0)]
                )
            ),
            PrintStmt(
                expression=CallExpr(
                    callee=var("add5"), paren=tok(TokenType.RIGHT_PAREN), arguments=[lit(2.0)]
                )
            ),
        ]
    )
    assert capsys.readouterr().out == "6\n11\n7\n"


def test_local_variable_does_not_leak_after_call():
    line = 5
    f = make_func(
        "f",
        [],
        [
            VarDeclStmt(name=name_tok("local"), initializer=lit(42.0)),
            make_return(var("local")),
        ],
    )
    stmts = [
        f,
        ExpressionStmt(expression=make_call("f", [])),
        PrintStmt(expression=VariableExpr(name_tok("local", line=line))),
    ]
    with pytest.raises(CodeFabRuntimeError, match=rf"\[{line}번째줄\] 미정의된 변수 'local'"):
        run(stmts)


def test_error_line_number_matches_call_site_not_declaration():
    call_line = 10
    add = make_func(
        "add", ["a", "b"], [make_return(bin_(var("a"), TokenType.PLUS, var("b")))], line=1
    )
    call = ExpressionStmt(expression=make_call("add", [lit(1.0)], line=call_line))
    with pytest.raises(
            CodeFabRuntimeError, match=rf"\[{call_line}번째줄\] 인자 개수가 일치하지 않습니다\."
    ):
        run([add, call])


def test_runtime_error_inside_recursive_call_propagates():
    line = 2
    bad_body = [
        IfStmt(
            condition=bin_(var("n"), TokenType.EQUAL_EQUAL, lit(0.0)),
            then_branch=BlockStmt(
                [make_return(UnaryExpr(operator=tok(TokenType.MINUS, line=line), right=lit("oops")))]
            ),
            else_branch=None,
        ),
        make_return(make_call("bad", [bin_(var("n"), TokenType.MINUS, lit(1.0))])),
    ]
    bad = make_func("bad", ["n"], bad_body)
    with pytest.raises(
            CodeFabRuntimeError, match=rf"\[{line}번째줄\] 피연산자는 반드시 숫자여야 합니다\."
    ):
        run([bad, ExpressionStmt(expression=make_call("bad", [lit(5.0)]))])


def test_independent_recursive_calls_in_same_expression(capsys):
    fact_body = [
        IfStmt(
            condition=bin_(var("n"), TokenType.LESS_EQUAL, lit(1.0)),
            then_branch=BlockStmt([make_return(lit(1.0))]),
            else_branch=None,
        ),
        make_return(
            bin_(var("n"), TokenType.STAR, make_call("fact", [bin_(var("n"), TokenType.MINUS, lit(1.0))]))
        ),
    ]
    fact = make_func("fact", ["n"], fact_body)
    run(
        [
            fact,
            PrintStmt(
                expression=bin_(
                    make_call("fact", [lit(3.0)]), TokenType.PLUS, make_call("fact", [lit(4.0)])
                )
            ),
        ]
    )
    assert capsys.readouterr().out == "30\n"


def test_argument_evaluation_order_is_left_to_right(capsys):
    record = make_func(
        "record",
        ["x"],
        [
            ExpressionStmt(
                expression=AssignExpr(name=name_tok("log"), value=bin_(var("log"), TokenType.PLUS, var("x")))
            ),
            make_return(var("x")),
        ],
    )
    noop2 = make_func("noop2", ["a", "b"], [make_return(lit(0.0))])
    run(
        [
            VarDeclStmt(name=name_tok("log"), initializer=lit("")),
            record,
            noop2,
            ExpressionStmt(
                expression=make_call(
                    "noop2", [make_call("record", [lit("A")]), make_call("record", [lit("B")])]
                )
            ),
            PrintStmt(expression=var("log")),
        ]
    )
    assert capsys.readouterr().out == "AB\n"


def test_zero_arg_function_called_with_extra_argument_raises():
    line = 2
    greet = make_func("greet", [], [make_return(lit("hi"))])
    call = ExpressionStmt(expression=make_call("greet", [lit(1.0)], line=line))
    with pytest.raises(
            CodeFabRuntimeError, match=rf"\[{line}번째줄\] 인자 개수가 일치하지 않습니다\."
    ):
        run([greet, call])
