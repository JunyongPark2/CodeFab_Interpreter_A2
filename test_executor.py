# test_executor.py
"""
Executor에 대한 pytest 테스트.
"""
import pytest

from ast_nodes import (
    PrintStmt, VarDeclStmt, ExpressionStmt, BlockStmt, IfStmt, ForStmt,
    LiteralExpr, VariableExpr, AssignExpr, GroupingExpr,
    UnaryExpr, BinaryExpr, LogicalExpr,
)
from tokens import Token, TokenType
from executor import Executor, LangRuntimeError


def tok(type_, origin="", value=None, line=1, col=1):
    return Token(type=type_, origin=origin, value=value, line=line, col=col)


def name_tok(name, line=1):
    return tok(TokenType.IDENTIFIER, origin=name, line=line)


def run(stmts):
    Executor(stmts).execute()


# ── PrintStmt / stringify ────────────────────────────────────────
def test_print_number(capsys):
    run([PrintStmt(expression=LiteralExpr(value=3.0))])
    assert capsys.readouterr().out == "3\n"


def test_print_float_keeps_decimal(capsys):
    run([PrintStmt(expression=LiteralExpr(value=3.5))])
    assert capsys.readouterr().out == "3.5\n"


def test_print_string(capsys):
    run([PrintStmt(expression=LiteralExpr(value="hello"))])
    assert capsys.readouterr().out == "hello\n"


def test_print_nil(capsys):
    run([PrintStmt(expression=LiteralExpr(value=None))])
    assert capsys.readouterr().out == "nil\n"


def test_print_bool(capsys):
    run([
        PrintStmt(expression=LiteralExpr(value=True)),
        PrintStmt(expression=LiteralExpr(value=False)),
    ])
    assert capsys.readouterr().out == "true\nfalse\n"


# ── VarDeclStmt / VariableExpr / AssignExpr ─────────────────────
def test_var_decl_with_initializer(capsys):
    run([
        VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(value=1.0)),
        PrintStmt(expression=VariableExpr(name=name_tok("x"))),
    ])
    assert capsys.readouterr().out == "1\n"


def test_var_decl_without_initializer_is_nil(capsys):
    run([
        VarDeclStmt(name=name_tok("x"), initializer=None),
        PrintStmt(expression=VariableExpr(name=name_tok("x"))),
    ])
    assert capsys.readouterr().out == "nil\n"


def test_assign_updates_existing_variable(capsys):
    run([
        VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(value=1.0)),
        ExpressionStmt(expression=AssignExpr(name=name_tok("x"), value=LiteralExpr(value=2.0))),
        PrintStmt(expression=VariableExpr(name=name_tok("x"))),
    ])
    assert capsys.readouterr().out == "2\n"


def test_assign_expression_evaluates_to_assigned_value(capsys):
    run([
        VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(value=1.0)),
        PrintStmt(expression=AssignExpr(name=name_tok("x"), value=LiteralExpr(value=9.0))),
    ])
    assert capsys.readouterr().out == "9\n"


# ── BlockStmt (스코프) ───────────────────────────────────────────
def test_block_shadows_outer_variable(capsys):
    run([
        VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(value=1.0)),
        BlockStmt(statements=[
            VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(value=2.0)),
            PrintStmt(expression=VariableExpr(name=name_tok("x"))),
        ]),
        PrintStmt(expression=VariableExpr(name=name_tok("x"))),
    ])
    assert capsys.readouterr().out == "2\n1\n"


def test_block_assignment_mutates_outer_variable(capsys):
    run([
        VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(value=1.0)),
        BlockStmt(statements=[
            ExpressionStmt(expression=AssignExpr(name=name_tok("x"), value=LiteralExpr(value=5.0))),
        ]),
        PrintStmt(expression=VariableExpr(name=name_tok("x"))),
    ])
    assert capsys.readouterr().out == "5\n"


def test_block_restores_environment_after_error():
    executor = Executor([
        VarDeclStmt(name=name_tok("x"), initializer=LiteralExpr(value=1.0)),
    ])
    executor.execute()
    with pytest.raises(LangRuntimeError):
        executor._exec_block(
            [ExpressionStmt(expression=UnaryExpr(
                operator=tok(TokenType.MINUS, line=1), right=LiteralExpr(value="not a number")))],
            env=executor._current,
        )
    assert executor._current is executor._global


# ── IfStmt ────────────────────────────────────────────────────────
def test_if_true_branch_executes(capsys):
    run([IfStmt(
        condition=LiteralExpr(value=True),
        then_branch=PrintStmt(expression=LiteralExpr(value="then")),
        else_branch=None,
    )])
    assert capsys.readouterr().out == "then\n"


def test_if_false_branch_runs_else(capsys):
    run([IfStmt(
        condition=LiteralExpr(value=False),
        then_branch=PrintStmt(expression=LiteralExpr(value="then")),
        else_branch=PrintStmt(expression=LiteralExpr(value="else")),
    )])
    assert capsys.readouterr().out == "else\n"


def test_if_false_without_else_prints_nothing(capsys):
    run([IfStmt(
        condition=LiteralExpr(value=False),
        then_branch=PrintStmt(expression=LiteralExpr(value="then")),
        else_branch=None,
    )])
    assert capsys.readouterr().out == ""


def test_if_condition_zero_is_truthy(capsys):
    # None과 False만 falsy이고 숫자 0.0은 truthy로 취급된다.
    run([IfStmt(
        condition=LiteralExpr(value=0.0),
        then_branch=PrintStmt(expression=LiteralExpr(value="truthy")),
        else_branch=None,
    )])
    assert capsys.readouterr().out == "truthy\n"


# ── ForStmt ───────────────────────────────────────────────────────
def test_for_loop_counts_up(capsys):
    run([ForStmt(
        initializer=VarDeclStmt(name=name_tok("i"), initializer=LiteralExpr(value=0.0)),
        condition=BinaryExpr(
            left=VariableExpr(name=name_tok("i")),
            operator=tok(TokenType.LESS, line=1),
            right=LiteralExpr(value=3.0),
        ),
        body=PrintStmt(expression=VariableExpr(name=name_tok("i"))),
        increment=AssignExpr(
            name=name_tok("i"),
            value=BinaryExpr(
                left=VariableExpr(name=name_tok("i")),
                operator=tok(TokenType.PLUS, line=1),
                right=LiteralExpr(value=1.0),
            ),
        ),
    )])
    assert capsys.readouterr().out == "0\n1\n2\n"


def test_for_loop_false_condition_never_runs(capsys):
    run([ForStmt(
        initializer=None,
        condition=LiteralExpr(value=False),
        body=PrintStmt(expression=LiteralExpr(value="unreachable")),
        increment=None,
    )])
    assert capsys.readouterr().out == ""


# ── BinaryExpr ────────────────────────────────────────────────────
def test_add_numbers(capsys):
    run([PrintStmt(expression=BinaryExpr(
        left=LiteralExpr(value=1.0), operator=tok(TokenType.PLUS, line=1), right=LiteralExpr(value=2.0),
    ))])
    assert capsys.readouterr().out == "3\n"


def test_add_strings(capsys):
    run([PrintStmt(expression=BinaryExpr(
        left=LiteralExpr(value="foo"), operator=tok(TokenType.PLUS, line=1), right=LiteralExpr(value="bar"),
    ))])
    assert capsys.readouterr().out == "foobar\n"


def test_add_mismatched_types_raises():
    with pytest.raises(LangRuntimeError):
        run([ExpressionStmt(expression=BinaryExpr(
            left=LiteralExpr(value=1.0), operator=tok(TokenType.PLUS, line=7), right=LiteralExpr(value="bar"),
        ))])


@pytest.mark.parametrize("op,left,right,expected", [
    (TokenType.MINUS, 5.0, 2.0, 3.0),
    (TokenType.STAR, 5.0, 2.0, 10.0),
    (TokenType.SLASH, 5.0, 2.0, 2.5),
])
def test_arithmetic_operators(op, left, right, expected, capsys):
    run([PrintStmt(expression=BinaryExpr(
        left=LiteralExpr(value=left), operator=tok(op, line=1), right=LiteralExpr(value=right),
    ))])
    out = capsys.readouterr().out.strip()
    assert float(out) == expected


@pytest.mark.parametrize("op", [TokenType.MINUS, TokenType.STAR, TokenType.SLASH, TokenType.GREATER, TokenType.LESS])
def test_arithmetic_non_number_operand_raises(op):
    with pytest.raises(LangRuntimeError):
        run([ExpressionStmt(expression=BinaryExpr(
            left=LiteralExpr(value="a"), operator=tok(op, line=1), right=LiteralExpr(value=1.0),
        ))])


def test_greater_and_less_comparisons(capsys):
    run([
        PrintStmt(expression=BinaryExpr(
            left=LiteralExpr(value=2.0), operator=tok(TokenType.GREATER, line=1), right=LiteralExpr(value=1.0))),
        PrintStmt(expression=BinaryExpr(
            left=LiteralExpr(value=2.0), operator=tok(TokenType.LESS, line=1), right=LiteralExpr(value=1.0))),
    ])
    assert capsys.readouterr().out == "true\nfalse\n"


@pytest.mark.parametrize("op,left,right,expected", [
    (TokenType.GREATER_EQUAL, 2.0, 1.0, True),
    (TokenType.GREATER_EQUAL, 1.0, 1.0, True),
    (TokenType.GREATER_EQUAL, 1.0, 2.0, False),
    (TokenType.LESS_EQUAL, 1.0, 2.0, True),
    (TokenType.LESS_EQUAL, 1.0, 1.0, True),
    (TokenType.LESS_EQUAL, 2.0, 1.0, False),
])
def test_greater_equal_and_less_equal_comparisons(op, left, right, expected, capsys):
    run([PrintStmt(expression=BinaryExpr(
        left=LiteralExpr(value=left), operator=tok(op, line=1), right=LiteralExpr(value=right),
    ))])
    assert capsys.readouterr().out == ("true\n" if expected else "false\n")


@pytest.mark.parametrize("op", [TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL])
def test_greater_equal_and_less_equal_non_number_operand_raises(op):
    with pytest.raises(LangRuntimeError):
        run([ExpressionStmt(expression=BinaryExpr(
            left=LiteralExpr(value="a"), operator=tok(op, line=1), right=LiteralExpr(value=1.0),
        ))])


@pytest.mark.parametrize("left,right,expected", [
    (1.0, 1.0, True),
    (1.0, 2.0, False),
    ("a", "a", True),
    ("a", "b", False),
    (True, True, True),
    (True, False, False),
    (None, None, True),
    (1.0, "1", False),   # 타입이 다르면 값이 같아 보여도 false
    (1.0, True, False),  # 숫자와 불린은 다른 타입으로 취급
])
def test_equal_equal_comparisons(left, right, expected, capsys):
    run([PrintStmt(expression=BinaryExpr(
        left=LiteralExpr(value=left), operator=tok(TokenType.EQUAL_EQUAL, line=1), right=LiteralExpr(value=right),
    ))])
    assert capsys.readouterr().out == ("true\n" if expected else "false\n")


@pytest.mark.parametrize("left,right,expected", [
    (1.0, 1.0, False),
    (1.0, 2.0, True),
    ("a", "a", False),
    ("a", "b", True),
])
def test_bang_equal_comparisons(left, right, expected, capsys):
    run([PrintStmt(expression=BinaryExpr(
        left=LiteralExpr(value=left), operator=tok(TokenType.BANG_EQUAL, line=1), right=LiteralExpr(value=right),
    ))])
    assert capsys.readouterr().out == ("true\n" if expected else "false\n")


# ── UnaryExpr ─────────────────────────────────────────────────────
def test_unary_minus(capsys):
    run([PrintStmt(expression=UnaryExpr(operator=tok(TokenType.MINUS, line=1), right=LiteralExpr(value=5.0)))])
    assert capsys.readouterr().out == "-5\n"


def test_unary_minus_non_number_raises():
    with pytest.raises(LangRuntimeError):
        run([ExpressionStmt(expression=UnaryExpr(
            operator=tok(TokenType.MINUS, line=2), right=LiteralExpr(value="a"),
        ))])


@pytest.mark.parametrize("value,expected", [(True, "false"), (False, "true"), (None, "true"), (1.0, "false")])
def test_unary_bang(value, expected, capsys):
    run([PrintStmt(expression=UnaryExpr(operator=tok(TokenType.BANG, line=1), right=LiteralExpr(value=value)))])
    assert capsys.readouterr().out == f"{expected}\n"


# ── GroupingExpr ──────────────────────────────────────────────────
def test_grouping_evaluates_inner_expression(capsys):
    run([PrintStmt(expression=GroupingExpr(expression=LiteralExpr(value=42.0)))])
    assert capsys.readouterr().out == "42\n"


# ── LogicalExpr (short-circuit) ───────────────────────────────────
def test_logical_or_short_circuits_on_truthy_left(capsys):
    run([PrintStmt(expression=LogicalExpr(
        left=LiteralExpr(value=True),
        operator=tok(TokenType.OR, line=1),
        right=VariableExpr(name=name_tok("undefined")),
    ))])
    assert capsys.readouterr().out == "true\n"


def test_logical_or_evaluates_right_when_left_falsy(capsys):
    run([PrintStmt(expression=LogicalExpr(
        left=LiteralExpr(value=False),
        operator=tok(TokenType.OR, line=1),
        right=LiteralExpr(value="fallback"),
    ))])
    assert capsys.readouterr().out == "fallback\n"


def test_logical_and_short_circuits_on_falsy_left(capsys):
    run([PrintStmt(expression=LogicalExpr(
        left=LiteralExpr(value=False),
        operator=tok(TokenType.AND, line=1),
        right=VariableExpr(name=name_tok("undefined")),
    ))])
    assert capsys.readouterr().out == "false\n"


def test_logical_and_evaluates_right_when_left_truthy(capsys):
    run([PrintStmt(expression=LogicalExpr(
        left=LiteralExpr(value=True),
        operator=tok(TokenType.AND, line=1),
        right=LiteralExpr(value="second"),
    ))])
    assert capsys.readouterr().out == "second\n"


# ── LangRuntimeError ──────────────────────────────────────────────
def test_lang_runtime_error_message_includes_line():
    err = LangRuntimeError(12, "문제 발생")
    assert str(err) == "[12번째줄] 문제 발생"


# ── PDF p.86 요구사항: 피연산자 타입 오류 시 어떤 문제인지 명시하여 보고 ──────
def test_bool_operand_raises():
    line = 1
    with pytest.raises(LangRuntimeError, match=rf"\[{line}번째줄\] 피연산자는 반드시 숫자여야 합니다\."):
        run([ExpressionStmt(expression=BinaryExpr(
            left=LiteralExpr(value=True), operator=tok(TokenType.STAR, line=line), right=LiteralExpr(value=False),
        ))])


def test_number_minus_string_raises():
    line = 1
    with pytest.raises(LangRuntimeError, match=rf"\[{line}번째줄\] 피연산자는 반드시 숫자여야 합니다\."):
        run([ExpressionStmt(expression=BinaryExpr(
            left=LiteralExpr(value=3.0), operator=tok(TokenType.MINUS, line=line), right=LiteralExpr(value="hello"),
        ))])

# ── PDF p.87 요구사항: 정의되지 않은 변수 참조 ──────
def test_assign_to_undefined_variable_raises():
    line = 1
    with pytest.raises(LangRuntimeError, match=rf"\[{line}번째줄\] 미정의된 변수 'undefined'"):
        run([
            ExpressionStmt(expression=AssignExpr(name=name_tok("undefined", line=line), value=LiteralExpr(value=1.0))),
        ])


def test_read_undefined_variable_raises():
    line = 1
    with pytest.raises(LangRuntimeError, match=rf"\[{line}번째줄\] 미정의된 변수 'undefined'"):
        run([PrintStmt(expression=VariableExpr(name=name_tok("undefined", line=line)))])


# ── PDF p.88 요구사항: 0으로 나누는 경우 런타임 오류 ──────
def test_division_by_zero_raises():
    line = 1
    with pytest.raises(LangRuntimeError, match=rf"\[{line}번째줄\] 0으로 나눈 오류"):
        run([ExpressionStmt(expression=BinaryExpr(
            left=LiteralExpr(value=3.0), operator=tok(TokenType.SLASH, line=line), right=LiteralExpr(value=0.0),
        ))])
