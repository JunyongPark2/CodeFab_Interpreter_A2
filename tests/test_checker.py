"""Checker Unit 테스트.

AST(list[Stmt])를 직접 구성해서 Checker의 입력으로 준다. 테스트 스크립트.md 기준:
  - "2) Checker Unit에서 검출하는 에러" 두 케이스는 Checker의 직접 책임 (에러 발생 검증)
  - "1) 정상동작 테스트"의 변수/블록스코프/shadowing/중첩스코프 케이스는
    Checker를 예외 없이 통과해야 한다 (Checker가 정상 코드를 막으면 안 됨)
"""

import pytest

from interpreter.ast_nodes import (
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    ExpressionStmt,
    ForStmt,
    IfStmt,
    LiteralExpr,
    PrintStmt,
    VarDeclStmt,
    VariableExpr,
)
from interpreter.checker import Checker, CheckError
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
