# test_executor.py
"""
Executor에 대한 pytest 테스트.

executor.py는 ast_nodes.py, environment.py, tokens.py 모듈에 의존하지만
현재 저장소에는 해당 모듈들이 존재하지 않는다. 아래 테스트는 executor.py의
동작(및 그것이 기대하는 AST/Token/Environment 인터페이스)을 명세하는
테스트이며, 세 모듈이 구현되어야 실행(수집)될 수 있다.

기대 인터페이스 요약:
- tokens.TokenType: MINUS, BANG, PLUS, STAR, SLASH, GREATER, LESS, OR, AND
- tokens.Token(type, text, value=None, line=0, col=0) - .type / .text / .value / .line / .col 속성 보유
- ast_nodes: PrintStmt(expression), VarDeclStmt(name, initializer),
  ExpressionStmt(expression), BlockStmt(statements),
  IfStmt(condition, then_branch, else_branch),
  ForStmt(initializer, condition, body, increment),
  LiteralExpr(value), VariableExpr(name), AssignExpr(name, value),
  GroupingExpr(expression), UnaryExpr(operator, right),
  BinaryExpr(left, operator, right), LogicalExpr(left, operator, right)
- environment.Environment(parent=None): define/get/assign
"""
import pytest
'''
from from ast_nodes import (
    PrintStmt, VarDeclStmt, ExpressionStmt, BlockStmt, IfStmt, ForStmt,
    LiteralExpr, VariableExpr, AssignExpr, GroupingExpr,
    UnaryExpr, BinaryExpr, LogicalExpr,
)
'''
from temp_implement import *
from tokens import Token, TokenType
from executor import Executor, LangRuntimeError


def tok(type_, text="", value=None, line=1, col=1):
    return Token(type=type_, text=text, value=value, line=line, col=col)


def name_tok(name, line=1):
    return tok(TokenType.IDENTIFIER, text=name, line=line)


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


def test_assign_to_undefined_variable_raises():
    with pytest.raises(Exception):
        run([
            ExpressionStmt(expression=AssignExpr(name=name_tok("undefined"), value=LiteralExpr(value=1.0))),
        ])


def test_read_undefined_variable_raises():
    with pytest.raises(Exception):
        run([PrintStmt(expression=VariableExpr(name=name_tok("undefined")))])


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


def test_division_by_zero_raises():
    with pytest.raises(LangRuntimeError, match="0으로 나눈"):
        run([ExpressionStmt(expression=BinaryExpr(
            left=LiteralExpr(value=1.0), operator=tok(TokenType.SLASH, line=3), right=LiteralExpr(value=0.0),
        ))])


def test_greater_and_less_comparisons(capsys):
    run([
        PrintStmt(expression=BinaryExpr(
            left=LiteralExpr(value=2.0), operator=tok(TokenType.GREATER, line=1), right=LiteralExpr(value=1.0))),
        PrintStmt(expression=BinaryExpr(
            left=LiteralExpr(value=2.0), operator=tok(TokenType.LESS, line=1), right=LiteralExpr(value=1.0))),
    ])
    assert capsys.readouterr().out == "true\nfalse\n"


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
