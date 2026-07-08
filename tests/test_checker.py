import pytest

from interpreter.ast_nodes import (
    ArrayExpr,
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    ExpressionStmt,
    ForStmt,
    GroupingExpr,
    IfStmt,
    IndexGetExpr,
    IndexSetExpr,
    LiteralExpr,
    PrintStmt,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from interpreter.checker import Checker
from interpreter.errors import CheckError
from interpreter.tokens import Token, TokenType


def ident(name: str, line: int = 1) -> Token:
    return Token(TokenType.IDENTIFIER, name, None, line)


def literal(value) -> LiteralExpr:
    return LiteralExpr(value)


# ── 에러 검출 테스트 (테스트 스크립트.md §2-2) ─────────────────


def test_self_reference_in_initializer_raises():
    # { var a = a; }
    stmts = [
        BlockStmt(
            [
                VarDeclStmt(ident("a"), VariableExpr(ident("a"))),
            ]
        )
    ]
    with pytest.raises(CheckError):
        Checker(stmts).check()


def test_duplicate_declaration_in_same_scope_raises():
    # { var a = "hi"; var a = 3; }
    stmts = [
        BlockStmt(
            [
                VarDeclStmt(ident("a"), literal("hi")),
                VarDeclStmt(ident("a"), literal(3.0)),
            ]
        )
    ]
    with pytest.raises(CheckError):
        Checker(stmts).check()


# ── 정상 동작 테스트 (테스트 스크립트.md §1-2) — 예외 없이 통과 ──


def test_reassignment_is_allowed():
    # var a = 10; a = a + 5;
    stmts = [
        VarDeclStmt(ident("a"), literal(10.0)),
        ExpressionStmt(AssignExpr(ident("a"), literal(15.0))),
    ]
    Checker(stmts).check()  # 예외 없어야 함


def test_shadowing_in_inner_block_is_allowed():
    # var x = "global"; { var x = "inner"; print x; } print x;
    stmts = [
        VarDeclStmt(ident("x"), literal("global")),
        BlockStmt(
            [
                VarDeclStmt(ident("x"), literal("inner")),
                PrintStmt(VariableExpr(ident("x"))),
            ]
        ),
        PrintStmt(VariableExpr(ident("x"))),
    ]
    Checker(stmts).check()


def test_modifying_outer_variable_without_redeclaration_is_allowed():
    # var count = 0; { count = count + 1; }
    stmts = [
        VarDeclStmt(ident("count"), literal(0.0)),
        BlockStmt(
            [
                ExpressionStmt(
                    AssignExpr(ident("count"), VariableExpr(ident("count")))
                ),
            ]
        ),
    ]
    Checker(stmts).check()


def test_nested_scope_variable_resolution_is_allowed():
    # var outer = "A"; { var inner = "B"; { print outer + inner; } }
    stmts = [
        VarDeclStmt(ident("outer"), literal("A")),
        BlockStmt(
            [
                VarDeclStmt(ident("inner"), literal("B")),
                BlockStmt(
                    [
                        PrintStmt(
                            BinaryExpr(
                                VariableExpr(ident("outer")),
                                Token(TokenType.PLUS, "+"),
                                VariableExpr(ident("inner")),
                            )
                        ),
                    ]
                ),
            ]
        ),
    ]
    Checker(stmts).check()


def test_duplicate_declaration_in_different_nested_scopes_is_allowed():
    # var a=2 in outer block, var a=7 in nested block -> 다른 스코프이므로 허용
    stmts = [
        BlockStmt(
            [
                VarDeclStmt(ident("a"), literal(2.0)),
                BlockStmt(
                    [
                        VarDeclStmt(ident("a"), literal(7.0)),
                    ]
                ),
            ]
        )
    ]
    Checker(stmts).check()


def test_var_decl_inside_if_branch_block_is_allowed():
    # if (true) { var a = 1; }
    stmts = [
        IfStmt(
            literal(True),
            BlockStmt([VarDeclStmt(ident("a"), literal(1.0))]),
            None,
        )
    ]
    Checker(stmts).check()


def test_for_loop_variable_scope_is_allowed():
    # for (var j = 0; j < 3; j = j + 1) { print j; }
    stmts = [
        ForStmt(
            initializer=VarDeclStmt(ident("j"), literal(0.0)),
            condition=BinaryExpr(
                VariableExpr(ident("j")), Token(TokenType.LESS, "<"), literal(3.0)
            ),
            increment=AssignExpr(
                ident("j"),
                BinaryExpr(
                    VariableExpr(ident("j")), Token(TokenType.PLUS, "+"), literal(1.0)
                ),
            ),
            body=BlockStmt([PrintStmt(VariableExpr(ident("j")))]),
        )
    ]
    Checker(stmts).check()


# ── 실행 전 최적화: 상수 폴딩 테스트 ─────────────────────────


def test_binary_arithmetic_is_folded_to_single_literal():
    # print 1 + 2 * 3; 은 (1 + 2 * 3) 통짜 리터럴 하나로 접히지는 않지만
    # 개별 이항식 단위로는 접힌다. 여기서는 리터럴+리터럴 단일 이항식만 확인한다.
    stmt = ExpressionStmt(
        BinaryExpr(literal(2.0), Token(TokenType.STAR, "*"), literal(3.0))
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value == 6.0


def test_string_concat_binary_is_folded():
    stmt = ExpressionStmt(
        BinaryExpr(literal("foo"), Token(TokenType.PLUS, "+"), literal("bar"))
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value == "foobar"


def test_comparison_binary_is_folded():
    stmt = ExpressionStmt(
        BinaryExpr(literal(1.0), Token(TokenType.LESS, "<"), literal(2.0))
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value is True


def test_nested_binary_expression_is_fully_folded():
    # (1 + 2) * 3 -> 자식이 먼저 접히고, 그 결과로 부모도 접혀서 최종 9.0 하나가 된다.
    stmt = ExpressionStmt(
        BinaryExpr(
            BinaryExpr(literal(1.0), Token(TokenType.PLUS, "+"), literal(2.0)),
            Token(TokenType.STAR, "*"),
            literal(3.0),
        )
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value == 9.0


def test_grouping_of_literal_is_unwrapped():
    stmt = ExpressionStmt(GroupingExpr(literal(5.0)))
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value == 5.0


def test_unary_minus_on_literal_is_folded():
    stmt = ExpressionStmt(UnaryExpr(Token(TokenType.MINUS, "-"), literal(3.0)))
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value == -3.0


def test_unary_bang_on_literal_is_folded():
    stmt = ExpressionStmt(UnaryExpr(Token(TokenType.BANG, "!"), literal(True)))
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value is False


def test_division_by_zero_is_not_folded():
    # 0으로 나누면 런타임 에러가 나야 하므로, Checker는 절대 이 식을 접으면 안 된다.
    stmt = ExpressionStmt(
        BinaryExpr(literal(1.0), Token(TokenType.SLASH, "/"), literal(0.0))
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression, BinaryExpr)


def test_type_mismatched_addition_is_not_folded():
    # 숫자 + 문자열은 런타임 에러가 나야 하므로 접으면 안 된다.
    stmt = ExpressionStmt(
        BinaryExpr(literal(1.0), Token(TokenType.PLUS, "+"), literal("a"))
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression, BinaryExpr)


def test_binary_with_variable_operand_is_not_folded():
    # 리터럴이 아닌 피연산자(변수)가 있으면 접을 수 없다.
    stmts = [
        VarDeclStmt(ident("a"), literal(1.0)),
        ExpressionStmt(
            BinaryExpr(
                VariableExpr(ident("a")), Token(TokenType.PLUS, "+"), literal(1.0)
            )
        ),
    ]
    Checker(stmts).check()
    assert isinstance(stmts[1].expression, BinaryExpr)


# ── 실행 전 최적화: 정적 바인딩 테스트 ─────────────────────────


def test_variable_in_nested_block_resolves_with_correct_distance():
    # { var a = 1; { var b = a + 1; print b; } }
    a_ref = VariableExpr(ident("a"))
    b_ref = VariableExpr(ident("b"))
    inner = BlockStmt(
        [
            VarDeclStmt(
                ident("b"), BinaryExpr(a_ref, Token(TokenType.PLUS, "+"), literal(1.0))
            ),
            PrintStmt(b_ref),
        ]
    )
    outer = BlockStmt([VarDeclStmt(ident("a"), literal(1.0)), inner])
    locals_map = Checker([outer]).check()

    assert locals_map[id(a_ref)] == 1
    assert locals_map[id(b_ref)] == 0


def test_top_level_global_variable_is_not_resolved():
    # var g = 1; print g; -> 전역 변수라서 locals_map에 안 남아야 한다.
    g_ref = VariableExpr(ident("g"))
    stmts = [VarDeclStmt(ident("g"), literal(1.0)), PrintStmt(g_ref)]
    locals_map = Checker(stmts).check()

    assert id(g_ref) not in locals_map


def test_undefined_variable_reference_is_not_resolved():
    ref = VariableExpr(ident("nope"))
    stmts = [PrintStmt(ref)]
    locals_map = Checker(stmts).check()

    assert id(ref) not in locals_map


def test_logical_expr_operands_are_checked_and_folded():
    from interpreter.ast_nodes import LogicalExpr

    stmt = ExpressionStmt(
        LogicalExpr(
            GroupingExpr(literal(True)),
            Token(TokenType.OR, "or"),
            GroupingExpr(literal(False)),
        )
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression.left, LiteralExpr)
    assert isinstance(stmt.expression.right, LiteralExpr)


@pytest.mark.parametrize(
    "op_type, op_text, left, right, expected",
    [
        (TokenType.MINUS, "-", 5.0, 2.0, 3.0),
        (TokenType.SLASH, "/", 6.0, 2.0, 3.0),
        (TokenType.GREATER, ">", 3.0, 2.0, True),
        (TokenType.GREATER_EQUAL, ">=", 2.0, 2.0, True),
        (TokenType.LESS_EQUAL, "<=", 2.0, 2.0, True),
        (TokenType.EQUAL_EQUAL, "==", 2.0, 2.0, True),
        (TokenType.BANG_EQUAL, "!=", 2.0, 3.0, True),
    ],
)
def test_binary_operators_are_folded(op_type, op_text, left, right, expected):
    stmt = ExpressionStmt(
        BinaryExpr(literal(left), Token(op_type, op_text), literal(right))
    )
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value == expected


def test_unary_bang_on_nil_is_folded_to_true():
    stmt = ExpressionStmt(UnaryExpr(Token(TokenType.BANG, "!"), literal(None)))
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value is True


def test_unary_bang_on_truthy_non_bool_is_folded_to_false():
    stmt = ExpressionStmt(UnaryExpr(Token(TokenType.BANG, "!"), literal("hi")))
    Checker([stmt]).check()
    assert isinstance(stmt.expression, LiteralExpr)
    assert stmt.expression.value is False


def test_assign_expr_in_nested_block_resolves_with_correct_distance():
    # { var a = 1; { a = 2; } }
    assign = AssignExpr(ident("a"), literal(2.0))
    stmts = [
        BlockStmt(
            [
                VarDeclStmt(ident("a"), literal(1.0)),
                BlockStmt([ExpressionStmt(assign)]),
            ]
        )
    ]
    locals_map = Checker(stmts).check()

    assert locals_map[id(assign)] == 1


# ── 정적배열 기능 — checker는 값 검증은 안 하고 하위 표현식만 순회한다 ──


def test_self_reference_inside_array_size_raises():
    # { var a = Array(a); }  — 크기 표현식 안의 자기참조도 잡아야 한다.
    stmts = [
        BlockStmt(
            [
                VarDeclStmt(
                    ident("a"),
                    ArrayExpr(VariableExpr(ident("a")), Token(TokenType.ARRAY, "Array")),
                ),
            ]
        )
    ]
    with pytest.raises(CheckError):
        Checker(stmts).check()


def test_self_reference_inside_index_get_expr_raises():
    # { var a = arr[a]; }  — 인덱스 표현식 안의 자기참조도 잡아야 한다.
    stmts = [
        VarDeclStmt(ident("arr"), literal(0.0)),
        BlockStmt(
            [
                VarDeclStmt(
                    ident("a"),
                    IndexGetExpr(
                        VariableExpr(ident("arr")),
                        Token(TokenType.LEFT_BRACKET, "["),
                        VariableExpr(ident("a")),
                    ),
                ),
            ]
        ),
    ]
    with pytest.raises(CheckError):
        Checker(stmts).check()


def test_index_set_with_defined_variables_is_allowed():
    # var arr = 0; var i = 0; arr[i] = 1;
    stmts = [
        VarDeclStmt(ident("arr"), literal(0.0)),
        VarDeclStmt(ident("i"), literal(0.0)),
        ExpressionStmt(
            IndexSetExpr(
                VariableExpr(ident("arr")),
                Token(TokenType.LEFT_BRACKET, "["),
                VariableExpr(ident("i")),
                literal(1.0),
            )
        ),
    ]
    Checker(stmts).check()
