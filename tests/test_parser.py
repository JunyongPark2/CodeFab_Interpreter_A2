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
    ImportStmt,
    IndexGetExpr,
    IndexSetExpr,
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from interpreter.errors import ParseError
from interpreter.parser import Parser
from interpreter.tokens import Token, TokenType

# ─────────────────────────────────────────────────────────
# 토큰 생성 헬퍼 — Tokenizer 없이 토큰을 직접 만든다
# ─────────────────────────────────────────────────────────


def num(v):
    """숫자 토큰. 예: num(3) → Token(NUMBER, "3", value=3.0)"""
    return Token(TokenType.NUMBER, str(v), float(v))


PLUS = Token(TokenType.PLUS, "+")
MINUS = Token(TokenType.MINUS, "-")
STAR = Token(TokenType.STAR, "*")
SLASH = Token(TokenType.SLASH, "/")
LESS = Token(TokenType.LESS, "<")
GREATER = Token(TokenType.GREATER, ">")
LPAREN = Token(TokenType.LEFT_PAREN, "(")
RPAREN = Token(TokenType.RIGHT_PAREN, ")")
TRUE = Token(TokenType.TRUE, "true")
FALSE = Token(TokenType.FALSE, "false")
PRINT = Token(TokenType.PRINT, "print")
SEMI = Token(TokenType.SEMICOLON, ";")
EOF = Token(TokenType.EOF, "")
VAR = Token(TokenType.VAR, "var")
EQUAL = Token(TokenType.EQUAL, "=")
LBRACE = Token(TokenType.LEFT_BRACE, "{")
RBRACE = Token(TokenType.RIGHT_BRACE, "}")
IF_KW = Token(TokenType.IF, "if")
ELSE_KW = Token(TokenType.ELSE, "else")
FOR_KW = Token(TokenType.FOR, "for")
AND_KW = Token(TokenType.AND, "and")
OR_KW = Token(TokenType.OR, "or")
BANG = Token(TokenType.BANG, "!")
# 정적배열 기능
ARRAY_KW = Token(TokenType.ARRAY, "Array")
LBRACKET = Token(TokenType.LEFT_BRACKET, "[")
RBRACKET = Token(TokenType.RIGHT_BRACKET, "]")


def ident(name: str) -> Token:
    """식별자(변수명) 토큰. 예: ident("a") → Token(IDENTIFIER, "a")"""
    return Token(TokenType.IDENTIFIER, name)


def string(v):
    """문자열 토큰. 예: string("hello") → Token(STRING, '"hello"', value="hello")"""
    return Token(TokenType.STRING, f'"{v}"', v)


def parse_print(*tokens):
    """`print <tokens> ;` 를 파싱해서 print 안의 표현식(Expr)을 꺼내준다."""
    stmts = Parser([PRINT, *tokens, SEMI, EOF]).parse()
    assert len(stmts) == 1
    assert isinstance(stmts[0], PrintStmt)
    return stmts[0].expression


# ─────────────────────────────────────────────────────────
# 테스트
# ─────────────────────────────────────────────────────────


def test_multiplication_precedes_addition():
    # print 1 + 2 * 3;
    #
    # 기대 트리:  +               (루트가 + 라는 것은 * 가 더 깊다 = 먼저 계산된다는 뜻)
    #            ├── 1
    #            └── *
    #                ├── 2
    #                └── 3
    expr = parse_print(num(1), PLUS, num(2), STAR, num(3))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS  # 루트는 +
    assert expr.left == LiteralExpr(1.0)  # 왼쪽은 1

    assert isinstance(expr.right, BinaryExpr)  # 오른쪽은 2 * 3
    assert expr.right.operator.type == TokenType.STAR
    assert expr.right.left == LiteralExpr(2.0)
    assert expr.right.right == LiteralExpr(3.0)


def test_parentheses_override_precedence():
    # print (1 + 2) * 3;
    #
    # 기대 트리:  *
    #            ├── Grouping( 1 + 2 )   ← 괄호 때문에 + 가 * 보다 깊어짐
    #            └── 3
    expr = parse_print(LPAREN, num(1), PLUS, num(2), RPAREN, STAR, num(3))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.STAR  # 루트는 *
    assert expr.right == LiteralExpr(3.0)

    assert isinstance(expr.left, GroupingExpr)  # 왼쪽은 괄호 묶음
    inner = expr.left.expression  # 괄호 안: 1 + 2
    assert isinstance(inner, BinaryExpr)
    assert inner.operator.type == TokenType.PLUS
    assert inner.left == LiteralExpr(1.0)
    assert inner.right == LiteralExpr(2.0)


def test_subtraction_is_left_associative():
    # print 10 - 4 - 3;
    #
    # (10 - 4) - 3 = 3 이 되려면 왼쪽부터 묶여야 한다.
    # 만약 10 - (4 - 3) = 9 로 묶이면 틀린 파서.
    #
    # 기대 트리:  -
    #            ├── -
    #            │   ├── 10
    #            │   └── 4
    #            └── 3
    expr = parse_print(num(10), MINUS, num(4), MINUS, num(3))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.MINUS
    assert expr.right == LiteralExpr(3.0)  # 오른쪽은 마지막 숫자 3

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 10 - 4
    assert expr.left.operator.type == TokenType.MINUS
    assert expr.left.left == LiteralExpr(10.0)
    assert expr.left.right == LiteralExpr(4.0)


def test_division_is_left_associative():
    # print 8 / 2 / 2;
    #
    # (8 / 2) / 2 = 2 가 되려면 왼쪽부터 묶여야 한다.
    #
    # 기대 트리:  /
    #            ├── /
    #            │   ├── 8
    #            │   └── 2
    #            └── 2
    expr = parse_print(num(8), SLASH, num(2), SLASH, num(2))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.SLASH
    assert expr.right == LiteralExpr(2.0)

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 8 / 2
    assert expr.left.operator.type == TokenType.SLASH
    assert expr.left.left == LiteralExpr(8.0)
    assert expr.left.right == LiteralExpr(2.0)


def test_unary_minus_precedes_addition():
    # print -3 + 2;
    #
    # (-3) + 2 = -1 이 되려면 - 가 3에만 붙어야 한다.
    #
    # 기대 트리:  +
    #            ├── Unary(-)
    #            │   └── 3
    #            └── 2
    expr = parse_print(MINUS, num(3), PLUS, num(2))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS  # 루트는 +
    assert expr.right == LiteralExpr(2.0)

    assert isinstance(expr.left, UnaryExpr)  # 왼쪽은 -3 (단항)
    assert expr.left.operator.type == TokenType.MINUS
    assert expr.left.right == LiteralExpr(3.0)


def test_less_than_operator():
    # print 1 < 2;
    #
    # 기대 트리:  <
    #            ├── 1
    #            └── 2
    expr = parse_print(num(1), LESS, num(2))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.LESS
    assert expr.left == LiteralExpr(1.0)
    assert expr.right == LiteralExpr(2.0)


def test_greater_than_operator():
    # print 3 > 5;
    #
    # 기대 트리:  >
    #            ├── 3
    #            └── 5
    expr = parse_print(num(3), GREATER, num(5))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.GREATER
    assert expr.left == LiteralExpr(3.0)
    assert expr.right == LiteralExpr(5.0)


def test_string_concatenation():
    # print "Hello, " + "CodeFab!";
    #
    # 기대 트리:  +
    #            ├── "Hello, "
    #            └── "CodeFab!"
    expr = parse_print(string("Hello, "), PLUS, string("CodeFab!"))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS
    assert expr.left == LiteralExpr("Hello, ")
    assert expr.right == LiteralExpr("CodeFab!")


def test_boolean_true_literal():
    # print true;
    #
    # 기대 트리:  LiteralExpr(True)
    expr = parse_print(TRUE)

    assert expr == LiteralExpr(True)


def test_boolean_false_literal():
    # print false;
    #
    # 기대 트리:  LiteralExpr(False)
    expr = parse_print(FALSE)

    assert expr == LiteralExpr(False)


# ─────────────────────────────────────────────────────────
# 변수, 할당, 블록 스코프, 변수 shadowing
# ─────────────────────────────────────────────────────────


def parse_stmts(*tokens) -> list:
    """토큰 목록을 파싱해 Stmt 리스트를 반환한다."""
    return Parser([*tokens, EOF]).parse()


def test_var_declaration():
    # var a = 10;
    #
    # 기대 트리:  VarDeclStmt(name="a", initializer=LiteralExpr(10.0))
    stmts = parse_stmts(VAR, ident("a"), EQUAL, num(10), SEMI)

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, VarDeclStmt)
    assert stmt.name.origin == "a"
    assert stmt.initializer == LiteralExpr(10.0)


def test_variable_reference():
    # var a = 10; var b = 20; print a + b;
    #
    # print 문 안의 기대 트리:  +
    #                           ├── VariableExpr("a")
    #                           └── VariableExpr("b")
    stmts = parse_stmts(
        VAR,
        ident("a"),
        EQUAL,
        num(10),
        SEMI,
        VAR,
        ident("b"),
        EQUAL,
        num(20),
        SEMI,
        PRINT,
        ident("a"),
        PLUS,
        ident("b"),
        SEMI,
    )

    assert len(stmts) == 3
    print_stmt = stmts[2]
    assert isinstance(print_stmt, PrintStmt)
    expr = print_stmt.expression
    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS
    assert isinstance(expr.left, VariableExpr)
    assert expr.left.name.origin == "a"
    assert isinstance(expr.right, VariableExpr)
    assert expr.right.name.origin == "b"


def test_reassignment():
    # a = a + 5;
    #
    # 기대 트리:  ExpressionStmt
    #              └── AssignExpr(name="a", value= + )
    #                                               ├── VariableExpr("a")
    #                                               └── 5
    stmts = parse_stmts(ident("a"), EQUAL, ident("a"), PLUS, num(5), SEMI)

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ExpressionStmt)
    expr = stmt.expression
    assert isinstance(expr, AssignExpr)
    assert expr.name.origin == "a"
    rhs = expr.value
    assert isinstance(rhs, BinaryExpr)
    assert rhs.operator.type == TokenType.PLUS
    assert isinstance(rhs.left, VariableExpr)
    assert rhs.left.name.origin == "a"
    assert rhs.right == LiteralExpr(5.0)


def test_block_scope():
    # { var x = "inner"; print x; }
    #
    # 기대 트리:  BlockStmt
    #              ├── VarDeclStmt("x", "inner")
    #              └── PrintStmt(VariableExpr("x"))
    stmts = parse_stmts(
        LBRACE,
        VAR,
        ident("x"),
        EQUAL,
        string("inner"),
        SEMI,
        PRINT,
        ident("x"),
        SEMI,
        RBRACE,
    )

    assert len(stmts) == 1
    block = stmts[0]
    assert isinstance(block, BlockStmt)
    assert len(block.statements) == 2
    inner_decl = block.statements[0]
    assert isinstance(inner_decl, VarDeclStmt)
    assert inner_decl.name.origin == "x"
    assert inner_decl.initializer == LiteralExpr("inner")
    print_stmt = block.statements[1]
    assert isinstance(print_stmt, PrintStmt)
    assert isinstance(print_stmt.expression, VariableExpr)
    assert print_stmt.expression.name.origin == "x"


def test_variable_shadowing():
    # var x = "global";
    # { var x = "inner"; print x; }
    # print x;
    #
    # 파서는 섀도잉을 "허용"하기만 하면 된다 (스코프 해석은 Executor 몫).
    # 구조적으로 바깥과 안쪽에 각각 VarDeclStmt(name="x")가 존재해야 한다.
    stmts = parse_stmts(
        VAR,
        ident("x"),
        EQUAL,
        string("global"),
        SEMI,
        LBRACE,
        VAR,
        ident("x"),
        EQUAL,
        string("inner"),
        SEMI,
        PRINT,
        ident("x"),
        SEMI,
        RBRACE,
        PRINT,
        ident("x"),
        SEMI,
    )

    assert len(stmts) == 3
    outer_decl = stmts[0]
    assert isinstance(outer_decl, VarDeclStmt)
    assert outer_decl.name.origin == "x"
    assert outer_decl.initializer == LiteralExpr("global")

    block = stmts[1]
    assert isinstance(block, BlockStmt)
    assert len(block.statements) == 2
    inner_decl = block.statements[0]
    assert isinstance(inner_decl, VarDeclStmt)
    assert inner_decl.name.origin == "x"
    assert inner_decl.initializer == LiteralExpr("inner")

    outer_print = stmts[2]
    assert isinstance(outer_print, PrintStmt)
    assert isinstance(outer_print.expression, VariableExpr)
    assert outer_print.expression.name.origin == "x"


def test_outer_variable_mutation():
    # var count = 0; { count = count + 1; } print count;
    #
    # 블록 안에서 var 재선언 없이 바깥 변수를 AssignExpr로 수정한다.
    stmts = parse_stmts(
        VAR,
        ident("count"),
        EQUAL,
        num(0),
        SEMI,
        LBRACE,
        ident("count"),
        EQUAL,
        ident("count"),
        PLUS,
        num(1),
        SEMI,
        RBRACE,
        PRINT,
        ident("count"),
        SEMI,
    )

    assert len(stmts) == 3
    assert isinstance(stmts[0], VarDeclStmt)

    block = stmts[1]
    assert isinstance(block, BlockStmt)
    assert len(block.statements) == 1
    assign_stmt = block.statements[0]
    assert isinstance(assign_stmt, ExpressionStmt)
    assign = assign_stmt.expression
    assert isinstance(assign, AssignExpr)
    assert assign.name.origin == "count"
    assert isinstance(assign.value, BinaryExpr)

    assert isinstance(stmts[2], PrintStmt)


def test_nested_scope():
    # var outer = "A";
    # { var inner = "B"; { print outer + inner; } }
    #
    # 기대 트리:  [VarDeclStmt("outer"), BlockStmt([
    #                VarDeclStmt("inner"),
    #                BlockStmt([PrintStmt(outer + inner)])
    #             ])]
    stmts = parse_stmts(
        VAR,
        ident("outer"),
        EQUAL,
        string("A"),
        SEMI,
        LBRACE,
        VAR,
        ident("inner"),
        EQUAL,
        string("B"),
        SEMI,
        LBRACE,
        PRINT,
        ident("outer"),
        PLUS,
        ident("inner"),
        SEMI,
        RBRACE,
        RBRACE,
    )

    assert len(stmts) == 2
    assert isinstance(stmts[0], VarDeclStmt)
    assert stmts[0].name.origin == "outer"

    outer_block = stmts[1]
    assert isinstance(outer_block, BlockStmt)
    assert len(outer_block.statements) == 2

    inner_decl = outer_block.statements[0]
    assert isinstance(inner_decl, VarDeclStmt)
    assert inner_decl.name.origin == "inner"

    inner_block = outer_block.statements[1]
    assert isinstance(inner_block, BlockStmt)
    assert len(inner_block.statements) == 1

    print_stmt = inner_block.statements[0]
    assert isinstance(print_stmt, PrintStmt)
    expr = print_stmt.expression
    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS
    assert isinstance(expr.left, VariableExpr)
    assert expr.left.name.origin == "outer"
    assert isinstance(expr.right, VariableExpr)
    assert expr.right.name.origin == "inner"


# ─────────────────────────────────────────────────────────
# 제어 흐름 — if/else, for
# ─────────────────────────────────────────────────────────


def test_if_true_simple():
    # if (true) print "bbq";
    #
    # 기대 트리:  IfStmt(condition=true, then=PrintStmt("bbq"), else=None)
    stmts = parse_stmts(
        IF_KW,
        LPAREN,
        TRUE,
        RPAREN,
        PRINT,
        string("bbq"),
        SEMI,
    )

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, IfStmt)
    assert stmt.condition == LiteralExpr(True)
    assert isinstance(stmt.then_branch, PrintStmt)
    assert stmt.then_branch.expression == LiteralExpr("bbq")
    assert stmt.else_branch is None


def test_if_else():
    # if (false) print "no"; else print "kfc";
    #
    # 기대 트리:  IfStmt(condition=false,
    #                    then=PrintStmt("no"),
    #                    else=PrintStmt("kfc"))
    stmts = parse_stmts(
        IF_KW,
        LPAREN,
        FALSE,
        RPAREN,
        PRINT,
        string("no"),
        SEMI,
        ELSE_KW,
        PRINT,
        string("kfc"),
        SEMI,
    )

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, IfStmt)
    assert stmt.condition == LiteralExpr(False)
    assert isinstance(stmt.then_branch, PrintStmt)
    assert stmt.then_branch.expression == LiteralExpr("no")
    assert isinstance(stmt.else_branch, PrintStmt)
    assert stmt.else_branch.expression == LiteralExpr("kfc")


def test_dangling_else_binds_to_nearest_if():
    # if (true) if (false) print "kfc"; else print "bbq";
    #
    # else 는 바깥 if 가 아니라 가장 가까운 if(false) 에 붙어야 한다.
    #
    # 기대 트리:  IfStmt(true,
    #              then=IfStmt(false,
    #                    then=PrintStmt("kfc"),
    #                    else=PrintStmt("bbq")),   ← 여기에 결합
    #              else=None)                      ← 바깥 if 에는 else 없음

    stmts = parse_stmts(
        IF_KW,
        LPAREN,
        TRUE,
        RPAREN,
        IF_KW,
        LPAREN,
        FALSE,
        RPAREN,
        PRINT,
        string("kfc"),
        SEMI,
        ELSE_KW,
        PRINT,
        string("bbq"),
        SEMI,
    )

    assert len(stmts) == 1
    outer = stmts[0]
    assert isinstance(outer, IfStmt)
    assert outer.condition == LiteralExpr(True)
    assert outer.else_branch is None  # 바깥 if 에는 else 없음

    inner = outer.then_branch
    assert isinstance(inner, IfStmt)
    assert inner.condition == LiteralExpr(False)
    assert isinstance(inner.then_branch, PrintStmt)
    assert inner.then_branch.expression == LiteralExpr("kfc")
    assert isinstance(inner.else_branch, PrintStmt)
    assert inner.else_branch.expression == LiteralExpr("bbq")


def test_for_loop():
    # for (var j = 0; j < 3; j = j + 1) { print j; }
    #
    # 기대 트리:  ForStmt(
    #               initializer = VarDeclStmt("j", 0),
    #               condition   = BinaryExpr(j < 3),
    #               increment   = AssignExpr("j", j + 1),
    #               body        = BlockStmt([PrintStmt(j)])
    #             )
    stmts = parse_stmts(
        FOR_KW,
        LPAREN,
        VAR,
        ident("j"),
        EQUAL,
        num(0),
        SEMI,
        ident("j"),
        LESS,
        num(3),
        SEMI,
        ident("j"),
        EQUAL,
        ident("j"),
        PLUS,
        num(1),
        RPAREN,
        LBRACE,
        PRINT,
        ident("j"),
        SEMI,
        RBRACE,
    )

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ForStmt)

    # initializer: var j = 0
    assert isinstance(stmt.initializer, VarDeclStmt)
    assert stmt.initializer.name.origin == "j"
    assert stmt.initializer.initializer == LiteralExpr(0.0)

    # condition: j < 3
    cond = stmt.condition
    assert isinstance(cond, BinaryExpr)
    assert cond.operator.type == TokenType.LESS
    assert isinstance(cond.left, VariableExpr)
    assert cond.left.name.origin == "j"
    assert cond.right == LiteralExpr(3.0)

    # increment: j = j + 1
    inc = stmt.increment
    assert isinstance(inc, AssignExpr)
    assert inc.name.origin == "j"
    rhs = inc.value
    assert isinstance(rhs, BinaryExpr)
    assert rhs.operator.type == TokenType.PLUS
    assert isinstance(rhs.left, VariableExpr)
    assert rhs.left.name.origin == "j"
    assert rhs.right == LiteralExpr(1.0)

    # body: { print j; }
    assert isinstance(stmt.body, BlockStmt)
    assert len(stmt.body.statements) == 1
    print_stmt = stmt.body.statements[0]
    assert isinstance(print_stmt, PrintStmt)
    assert isinstance(print_stmt.expression, VariableExpr)
    assert print_stmt.expression.name.origin == "j"


# ─────────────────────────────────────────────────────────
# ParseError 테스트 — 잘못된 코드가 반드시 오류를 raise 해야 한다
# ─────────────────────────────────────────────────────────


def test_missing_semicolon_after_expression():
    # print 1 + 2   ← ';' 없음
    # → [N번째줄] ';' 가 필요합니다.
    with pytest.raises(ParseError, match="';' 가 필요합니다"):
        Parser([PRINT, num(1), PLUS, num(2), EOF]).parse()


def test_missing_semicolon_after_print_string():
    # print "hello"   ← ';' 없음
    with pytest.raises(ParseError, match="';' 가 필요합니다"):
        Parser([PRINT, string("hello"), EOF]).parse()


def test_missing_semicolon_after_var_declaration():
    # var a = 10   ← ';' 없음
    with pytest.raises(ParseError, match="';' 가 필요합니다"):
        Parser([VAR, ident("a"), EQUAL, num(10), EOF]).parse()


def test_missing_closing_paren_in_grouping():
    # print (1 + 2;   ← ')' 없음
    # → [N번째줄] ')' 가 필요합니다.
    with pytest.raises(ParseError, match="'\\)' 가 필요합니다"):
        Parser([PRINT, LPAREN, num(1), PLUS, num(2), SEMI, EOF]).parse()


def test_missing_closing_paren_in_if_condition():
    # if (true { print "x"; }   ← ')' 없음
    with pytest.raises(ParseError, match="'\\)' 가 필요합니다"):
        Parser(
            [
                IF_KW,
                LPAREN,
                TRUE,
                LBRACE,
                PRINT,
                string("x"),
                SEMI,
                RBRACE,
                EOF,
            ]
        ).parse()


def test_invalid_assignment_target():
    # a + b = 3;   ← 대입 대상이 VariableExpr이 아님
    # → [N번째줄] 대입 대상이 올바르지 않습니다.
    with pytest.raises(ParseError, match="대입 대상이 올바르지 않습니다"):
        Parser(
            [
                ident("a"),
                PLUS,
                ident("b"),
                EQUAL,
                num(3),
                SEMI,
                EOF,
            ]
        ).parse()


def test_unexpected_token_in_expression_position():
    # print * 5;   ← '*' 는 표현식 시작이 될 수 없음
    # → [N번째줄] 표현식이 필요합니다.
    with pytest.raises(ParseError, match="표현식이 필요합니다"):
        Parser([PRINT, STAR, num(5), SEMI, EOF]).parse()


def test_missing_expression_before_semicolon():
    # print ;   ← 표현식 자리에 ';'
    with pytest.raises(ParseError, match="표현식이 필요합니다"):
        Parser([PRINT, SEMI, EOF]).parse()


def test_missing_closing_brace_in_block():
    # { var a = 1;   ← '}' 없음
    # → [N번째줄] '}' 가 필요합니다.
    with pytest.raises(ParseError, match="'\\}' 가 필요합니다"):
        Parser([LBRACE, VAR, ident("a"), EQUAL, num(1), SEMI, EOF]).parse()


def test_missing_variable_name_in_declaration():
    # var = 10;   ← 변수 이름이 없음
    # → [N번째줄] 변수 이름이 필요합니다.
    with pytest.raises(ParseError, match="변수 이름이 필요합니다"):
        Parser([VAR, EQUAL, num(10), SEMI, EOF]).parse()


# ─────────────────────────────────────────────────────────
# 논리 연산 — and / or
# ─────────────────────────────────────────────────────────


def test_and_basic():
    # print true and false;
    #
    # 기대 트리:  LogicalExpr(and)
    #            ├── LiteralExpr(True)
    #            └── LiteralExpr(False)
    expr = parse_print(TRUE, AND_KW, FALSE)

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.AND
    assert expr.left == LiteralExpr(True)
    assert expr.right == LiteralExpr(False)


def test_or_basic():
    # print false or true;
    #
    # 기대 트리:  LogicalExpr(or)
    #            ├── LiteralExpr(False)
    #            └── LiteralExpr(True)
    expr = parse_print(FALSE, OR_KW, TRUE)

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.OR
    assert expr.left == LiteralExpr(False)
    assert expr.right == LiteralExpr(True)


def test_and_precedes_or():
    # print true or false and false;
    #
    # and 가 or 보다 우선순위가 높으므로 false and false 가 먼저 묶여야 한다.
    #
    # 기대 트리:  LogicalExpr(or)          ← 루트가 or
    #            ├── LiteralExpr(True)
    #            └── LogicalExpr(and)      ← and 가 더 깊음
    #                ├── LiteralExpr(False)
    #                └── LiteralExpr(False)
    expr = parse_print(TRUE, OR_KW, FALSE, AND_KW, FALSE)

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.OR  # 루트는 or
    assert expr.left == LiteralExpr(True)

    assert isinstance(expr.right, LogicalExpr)  # 오른쪽은 false and false
    assert expr.right.operator.type == TokenType.AND
    assert expr.right.left == LiteralExpr(False)
    assert expr.right.right == LiteralExpr(False)


def test_and_chain_is_left_associative():
    # print true and false and true;
    #
    # 왼쪽 결합: (true and false) and true
    #
    # 기대 트리:  LogicalExpr(and)
    #            ├── LogicalExpr(and)
    #            │   ├── LiteralExpr(True)
    #            │   └── LiteralExpr(False)
    #            └── LiteralExpr(True)
    expr = parse_print(TRUE, AND_KW, FALSE, AND_KW, TRUE)

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.AND
    assert expr.right == LiteralExpr(True)

    assert isinstance(expr.left, LogicalExpr)
    assert expr.left.operator.type == TokenType.AND
    assert expr.left.left == LiteralExpr(True)
    assert expr.left.right == LiteralExpr(False)


def test_or_chain_is_left_associative():
    # print false or true or false;
    #
    # 왼쪽 결합: (false or true) or false
    #
    # 기대 트리:  LogicalExpr(or)
    #            ├── LogicalExpr(or)
    #            │   ├── LiteralExpr(False)
    #            │   └── LiteralExpr(True)
    #            └── LiteralExpr(False)
    expr = parse_print(FALSE, OR_KW, TRUE, OR_KW, FALSE)

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.OR
    assert expr.right == LiteralExpr(False)

    assert isinstance(expr.left, LogicalExpr)
    assert expr.left.operator.type == TokenType.OR
    assert expr.left.left == LiteralExpr(False)
    assert expr.left.right == LiteralExpr(True)


def test_bang_negates_true():
    # print !true;
    #
    # 기대 트리:  UnaryExpr(!)
    #            └── LiteralExpr(True)
    expr = parse_print(BANG, TRUE)

    assert isinstance(expr, UnaryExpr)
    assert expr.operator.type == TokenType.BANG
    assert expr.right == LiteralExpr(True)


def test_bang_negates_false():
    # print !false;
    #
    # 기대 트리:  UnaryExpr(!)
    #            └── LiteralExpr(False)
    expr = parse_print(BANG, FALSE)

    assert isinstance(expr, UnaryExpr)
    assert expr.operator.type == TokenType.BANG
    assert expr.right == LiteralExpr(False)


def test_double_bang_negation():
    # print !!true;
    #
    # 기대 트리:  UnaryExpr(!)        ← 바깥 !
    #            └── UnaryExpr(!)    ← 안쪽 !
    #                └── LiteralExpr(True)
    expr = parse_print(BANG, BANG, TRUE)

    assert isinstance(expr, UnaryExpr)
    assert expr.operator.type == TokenType.BANG
    assert isinstance(expr.right, UnaryExpr)
    assert expr.right.operator.type == TokenType.BANG
    assert expr.right.right == LiteralExpr(True)


def test_bang_precedes_and():
    # print !true and false;
    #
    # !는 and보다 우선순위가 높으므로 !true 가 먼저 묶여야 한다.
    #
    # 기대 트리:  LogicalExpr(and)
    #            ├── UnaryExpr(!)
    #            │   └── LiteralExpr(True)
    #            └── LiteralExpr(False)
    expr = parse_print(BANG, TRUE, AND_KW, FALSE)

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.AND

    assert isinstance(expr.left, UnaryExpr)
    assert expr.left.operator.type == TokenType.BANG
    assert expr.left.right == LiteralExpr(True)

    assert expr.right == LiteralExpr(False)


def test_bang_applied_to_variable():
    # print !isExist;
    #
    # 기대 트리:  UnaryExpr(!)
    #            └── VariableExpr("isExist")
    expr = parse_print(BANG, ident("isExist"))

    assert isinstance(expr, UnaryExpr)
    assert expr.operator.type == TokenType.BANG
    assert isinstance(expr.right, VariableExpr)
    assert expr.right.name.origin == "isExist"


def test_and_with_comparison_operands():
    # print 1 < 2 and 3 > 0;
    #
    # 비교식이 and 의 피연산자가 된다.
    #
    # 기대 트리:  LogicalExpr(and)
    #            ├── BinaryExpr(<)
    #            │   ├── LiteralExpr(1.0)
    #            │   └── LiteralExpr(2.0)
    #            └── BinaryExpr(>)
    #                ├── LiteralExpr(3.0)
    #                └── LiteralExpr(0.0)
    expr = parse_print(num(1), LESS, num(2), AND_KW, num(3), GREATER, num(0))

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.AND

    assert isinstance(expr.left, BinaryExpr)
    assert expr.left.operator.type == TokenType.LESS
    assert expr.left.left == LiteralExpr(1.0)
    assert expr.left.right == LiteralExpr(2.0)

    assert isinstance(expr.right, BinaryExpr)
    assert expr.right.operator.type == TokenType.GREATER
    assert expr.right.left == LiteralExpr(3.0)
    assert expr.right.right == LiteralExpr(0.0)


# ─────────────────────────────────────────────────────────
# equality vs comparison 우선순위
# 가이드 BNF: equality → comparison (("==" | "!=") comparison)*
#             comparison → term ((">" | ">=" | "<" | "<=") term)*
# 즉, < > <= >= 는 == != 보다 우선순위가 높아야 한다.
# ─────────────────────────────────────────────────────────


def test_equality_has_lower_precedence_than_comparison():
    # print 1 == 2 < 3;
    #
    # < 가 == 보다 우선순위가 높으므로 2 < 3 이 먼저 묶여야 한다.
    #
    # 기대 트리:  ==                  ← 루트가 ==
    #            ├── LiteralExpr(1.0)
    #            └── BinaryExpr(<)    ← < 가 더 깊음 (먼저 계산)
    #                ├── LiteralExpr(2.0)
    #                └── LiteralExpr(3.0)
    EQUAL_EQUAL = Token(TokenType.EQUAL_EQUAL, "==")
    expr = parse_print(num(1), EQUAL_EQUAL, num(2), LESS, num(3))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.EQUAL_EQUAL  # 루트는 ==

    assert expr.left == LiteralExpr(1.0)

    assert isinstance(expr.right, BinaryExpr)  # 오른쪽은 2 < 3
    assert expr.right.operator.type == TokenType.LESS
    assert expr.right.left == LiteralExpr(2.0)
    assert expr.right.right == LiteralExpr(3.0)


def test_inequality_has_lower_precedence_than_comparison():
    # print 5 != 3 > 1;
    #
    # > 가 != 보다 우선순위가 높으므로 3 > 1 이 먼저 묶여야 한다.
    #
    # 기대 트리 (가이드 명세):  !=
    #                           ├── LiteralExpr(5.0)
    #                           └── BinaryExpr(>)
    #                               ├── LiteralExpr(3.0)
    #                               └── LiteralExpr(1.0)
    BANG_EQUAL = Token(TokenType.BANG_EQUAL, "!=")
    GREATER_OP = Token(TokenType.GREATER, ">")
    expr = parse_print(num(5), BANG_EQUAL, num(3), GREATER_OP, num(1))

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.BANG_EQUAL  # 루트는 !=

    assert expr.left == LiteralExpr(5.0)

    assert isinstance(expr.right, BinaryExpr)  # 오른쪽은 3 > 1
    assert expr.right.operator.type == TokenType.GREATER
    assert expr.right.left == LiteralExpr(3.0)
    assert expr.right.right == LiteralExpr(1.0)


# ─────────────────────────────────────────────────────────
# and/or + equality/comparison 혼합 우선순위
# 전체 체인: logic_or → logic_and → equality → comparison
# ─────────────────────────────────────────────────────────


def test_equality_precedes_and():
    # print 1 == 1 and 2 != 3;
    #
    # == 과 != 이 and 보다 먼저 묶여야 한다.
    #
    # 기대 트리:  LogicalExpr(and)        ← 루트가 and
    #            ├── BinaryExpr(==)
    #            │   ├── LiteralExpr(1.0)
    #            │   └── LiteralExpr(1.0)
    #            └── BinaryExpr(!=)
    #                ├── LiteralExpr(2.0)
    #                └── LiteralExpr(3.0)
    EQUAL_EQUAL = Token(TokenType.EQUAL_EQUAL, "==")
    BANG_EQUAL = Token(TokenType.BANG_EQUAL, "!=")
    expr = parse_print(num(1), EQUAL_EQUAL, num(1), AND_KW, num(2), BANG_EQUAL, num(3))

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.AND  # 루트는 and

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 1 == 1
    assert expr.left.operator.type == TokenType.EQUAL_EQUAL
    assert expr.left.left == LiteralExpr(1.0)
    assert expr.left.right == LiteralExpr(1.0)

    assert isinstance(expr.right, BinaryExpr)  # 오른쪽은 2 != 3
    assert expr.right.operator.type == TokenType.BANG_EQUAL
    assert expr.right.left == LiteralExpr(2.0)
    assert expr.right.right == LiteralExpr(3.0)


def test_full_precedence_chain_or_and_equality_comparison():
    # print 1 == 1 or 2 == 3 and 4 < 5;
    #
    # 우선순위: < > == != → and → or  (낮을수록 루트에 가까움)
    # 따라서: 4 < 5 가 먼저, 2 == 3 이 다음, and 로 묶이고, or 가 마지막
    #
    # 기대 트리:  LogicalExpr(or)              ← 루트가 or
    #            ├── BinaryExpr(==)            ← 1 == 1
    #            │   ├── LiteralExpr(1.0)
    #            │   └── LiteralExpr(1.0)
    #            └── LogicalExpr(and)          ← and 가 or 보다 깊음
    #                ├── BinaryExpr(==)        ← 2 == 3
    #                │   ├── LiteralExpr(2.0)
    #                │   └── LiteralExpr(3.0)
    #                └── BinaryExpr(<)         ← 4 < 5
    #                    ├── LiteralExpr(4.0)
    #                    └── LiteralExpr(5.0)
    EQUAL_EQUAL = Token(TokenType.EQUAL_EQUAL, "==")
    expr = parse_print(
        num(1),
        EQUAL_EQUAL,
        num(1),
        OR_KW,
        num(2),
        EQUAL_EQUAL,
        num(3),
        AND_KW,
        num(4),
        LESS,
        num(5),
    )

    assert isinstance(expr, LogicalExpr)
    assert expr.operator.type == TokenType.OR  # 루트는 or

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 1 == 1
    assert expr.left.operator.type == TokenType.EQUAL_EQUAL
    assert expr.left.left == LiteralExpr(1.0)
    assert expr.left.right == LiteralExpr(1.0)

    rhs = expr.right
    assert isinstance(rhs, LogicalExpr)  # 오른쪽은 and
    assert rhs.operator.type == TokenType.AND

    assert isinstance(rhs.left, BinaryExpr)  # and 왼쪽은 2 == 3
    assert rhs.left.operator.type == TokenType.EQUAL_EQUAL
    assert rhs.left.left == LiteralExpr(2.0)
    assert rhs.left.right == LiteralExpr(3.0)

    assert isinstance(rhs.right, BinaryExpr)  # and 오른쪽은 4 < 5
    assert rhs.right.operator.type == TokenType.LESS
    assert rhs.right.left == LiteralExpr(4.0)
    assert rhs.right.right == LiteralExpr(5.0)


# ─────────────────────────────────────────────────────────
# 정적배열 기능 — Array(size) 생성, arr[index] 읽기/쓰기
# ─────────────────────────────────────────────────────────


def test_array_creation():
    # var arr = Array(3);
    #
    # 기대 트리:  VarDeclStmt(name="arr", initializer=ArrayExpr(size=3))
    stmts = parse_stmts(
        VAR, ident("arr"), EQUAL, ARRAY_KW, LPAREN, num(3), RPAREN, SEMI
    )

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, VarDeclStmt)
    assert stmt.name.origin == "arr"
    assert isinstance(stmt.initializer, ArrayExpr)
    assert stmt.initializer.size == LiteralExpr(3.0)


def test_index_read():
    # print arr[0];
    #
    # 기대 트리:  IndexGetExpr(array=VariableExpr("arr"), index=0)
    expr = parse_print(ident("arr"), LBRACKET, num(0), RBRACKET)

    assert isinstance(expr, IndexGetExpr)
    assert isinstance(expr.array, VariableExpr)
    assert expr.array.name.origin == "arr"
    assert expr.index == LiteralExpr(0.0)


def test_index_write():
    # arr[0] = 10;
    #
    # 기대 트리:  ExpressionStmt
    #              └── IndexSetExpr(array="arr", index=0, value=10)
    stmts = parse_stmts(ident("arr"), LBRACKET, num(0), RBRACKET, EQUAL, num(10), SEMI)

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ExpressionStmt)
    expr = stmt.expression
    assert isinstance(expr, IndexSetExpr)
    assert isinstance(expr.array, VariableExpr)
    assert expr.array.name.origin == "arr"
    assert expr.index == LiteralExpr(0.0)
    assert expr.value == LiteralExpr(10.0)


def test_index_write_with_expression_index():
    # arr[i - 1] = 7;
    #
    # 인덱스 자리에도 임의의 표현식이 올 수 있어야 한다.
    stmts = parse_stmts(
        ident("arr"),
        LBRACKET,
        ident("i"),
        MINUS,
        num(1),
        RBRACKET,
        EQUAL,
        num(7),
        SEMI,
    )

    assert len(stmts) == 1
    expr = stmts[0].expression
    assert isinstance(expr, IndexSetExpr)
    assert isinstance(expr.index, BinaryExpr)
    assert expr.index.operator.type == TokenType.MINUS
    assert expr.value == LiteralExpr(7.0)


def test_missing_closing_paren_in_array_creation():
    # var arr = Array(3;   ← ')' 없음
    with pytest.raises(ParseError, match="'\\)' 가 필요합니다"):
        Parser([VAR, ident("arr"), EQUAL, ARRAY_KW, LPAREN, num(3), SEMI, EOF]).parse()


def test_missing_closing_bracket_in_index():
    # print arr[0;   ← ']' 없음
    with pytest.raises(ParseError, match="'\\]' 가 필요합니다"):
        Parser([PRINT, ident("arr"), LBRACKET, num(0), SEMI, EOF]).parse()


# ── import 문법 (가이드 5-5) ────────────────────────────────
IMPORT_KW = Token(TokenType.IMPORT, "import")
ALIAS_KW = Token(TokenType.ALIAS, "alias")


def test_import_statement():
    # import "sum.txt" alias sum;
    stmts = parse_stmts(IMPORT_KW, string("sum.txt"), ALIAS_KW, ident("sum"), SEMI)

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ImportStmt)
    assert stmt.path.value == "sum.txt"
    assert stmt.alias.origin == "sum"


def test_import_missing_alias_keyword_raises():
    # import "sum.txt" sum;   ← alias 키워드 없음
    with pytest.raises(ParseError, match="'alias'"):
        Parser([IMPORT_KW, string("sum.txt"), ident("sum"), SEMI, EOF]).parse()


def test_import_path_must_be_string_literal():
    # import sum alias sum;   ← 경로가 문자열이 아님
    with pytest.raises(ParseError):
        Parser([IMPORT_KW, ident("sum"), ALIAS_KW, ident("sum"), SEMI, EOF]).parse()


def test_import_allowed_at_top_level_after_a_for_loop():
    # for (;false;) { print 1; } import "sum.txt" alias sum;
    stmts = parse_stmts(
        FOR_KW,
        LPAREN,
        SEMI,
        FALSE,
        SEMI,
        RPAREN,
        PRINT,
        num(1),
        SEMI,
        IMPORT_KW,
        string("sum.txt"),
        ALIAS_KW,
        ident("sum"),
        SEMI,
    )
    assert len(stmts) == 2
    assert isinstance(stmts[1], ImportStmt)


def test_import_allowed_inside_if_body():
    # if (true) { import "sum.txt" alias sum; }
    stmts = parse_stmts(
        IF_KW,
        LPAREN,
        TRUE,
        RPAREN,
        LBRACE,
        IMPORT_KW,
        string("sum.txt"),
        ALIAS_KW,
        ident("sum"),
        SEMI,
        RBRACE,
    )
    assert isinstance(stmts[0].then_branch.statements[0], ImportStmt)


def test_import_directly_inside_for_body_raises():
    # for (;false;) { import "sum.txt" alias sum; }
    with pytest.raises(ParseError, match="반복문 내부"):
        Parser(
            [
                FOR_KW,
                LPAREN,
                SEMI,
                FALSE,
                SEMI,
                RPAREN,
                LBRACE,
                IMPORT_KW,
                string("sum.txt"),
                ALIAS_KW,
                ident("sum"),
                SEMI,
                RBRACE,
                EOF,
            ]
        ).parse()


def test_import_inside_nested_block_inside_for_body_raises():
    # for (;false;) { { import "sum.txt" alias sum; } }  ← 중첩 블록 안이어도 금지
    with pytest.raises(ParseError, match="반복문 내부"):
        Parser(
            [
                FOR_KW,
                LPAREN,
                SEMI,
                FALSE,
                SEMI,
                RPAREN,
                LBRACE,
                LBRACE,
                IMPORT_KW,
                string("sum.txt"),
                ALIAS_KW,
                ident("sum"),
                SEMI,
                RBRACE,
                RBRACE,
                EOF,
            ]
        ).parse()


def test_import_inside_if_body_inside_for_body_raises():
    # for (;false;) { if (true) { import "sum.txt" alias sum; } }
    with pytest.raises(ParseError, match="반복문 내부"):
        Parser(
            [
                FOR_KW,
                LPAREN,
                SEMI,
                FALSE,
                SEMI,
                RPAREN,
                LBRACE,
                IF_KW,
                LPAREN,
                TRUE,
                RPAREN,
                LBRACE,
                IMPORT_KW,
                string("sum.txt"),
                ALIAS_KW,
                ident("sum"),
                SEMI,
                RBRACE,
                RBRACE,
                EOF,
            ]
        ).parse()


def test_import_forbidden_depth_restored_after_nested_for_loop():
    # for (;false;) { for (;false;) { print 1; } } import "sum.txt" alias sum;
    # 중첩 for 하나가 끝나도 바깥 for 안이면 여전히 금지되고, 둘 다 끝나면 다시 허용된다.
    stmts = parse_stmts(
        FOR_KW,
        LPAREN,
        SEMI,
        FALSE,
        SEMI,
        RPAREN,
        LBRACE,
        FOR_KW,
        LPAREN,
        SEMI,
        FALSE,
        SEMI,
        RPAREN,
        PRINT,
        num(1),
        SEMI,
        RBRACE,
        IMPORT_KW,
        string("sum.txt"),
        ALIAS_KW,
        ident("sum"),
        SEMI,
    )
    assert len(stmts) == 2
    assert isinstance(stmts[1], ImportStmt)
