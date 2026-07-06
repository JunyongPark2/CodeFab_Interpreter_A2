# test_parser.py — Parser 유닛 테스트 (TDD: 구현 전 작성)
#
# 실행: pytest test_parser.py -v
#
# 테스트 대상 (test_sample.md 산술/우선순위 5줄):
#   print 1 + 2 * 3;        // expect: 7
#   print (1 + 2) * 3;      // expect: 9
#   print 10 - 4 - 3;       // expect: 3
#   print 8 / 2 / 2;        // expect: 2
#   print -3 + 2;           // expect: -1
#
# 비교 / 동등성:
#   print 1 < 2;            // expect: true
#   print 3 > 5;            // expect: false
#
# 문자열 연결:
#   print "Hello, " + "CodeFab!";   // expect: Hello, CodeFab!
#
# Parser는 "계산"을 하지 않는다. 계산은 Executor의 몫.
# Parser의 책임은 올바른 "모양의 트리"를 만드는 것이므로,
# 여기서는 트리의 모양(구조)만 검사한다.
from ast_nodes import (
    LiteralExpr, BinaryExpr, UnaryExpr, GroupingExpr, PrintStmt,
)
from parser import Parser
from tokens import Token, TokenType


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

def test_곱셈이_덧셈보다_먼저():
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


def test_괄호가_우선순위를_이긴다():
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


def test_뺄셈은_왼쪽부터_묶인다():
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


def test_나눗셈은_왼쪽부터_묶인다():
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


def test_단항_마이너스는_덧셈보다_먼저():
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


def test_비교_작다():
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


def test_비교_크다():
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


def test_문자열_연결():
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


def test_불리언_참():
    # print true;
    #
    # 기대 트리:  LiteralExpr(True)
    expr = parse_print(TRUE)

    assert expr == LiteralExpr(True)


def test_불리언_거짓():
    # print false;
    #
    # 기대 트리:  LiteralExpr(False)
    expr = parse_print(FALSE)

    assert expr == LiteralExpr(False)
