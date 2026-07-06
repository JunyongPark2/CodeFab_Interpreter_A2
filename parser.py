# parser.py — Parser, ParseError (박준용, 송지영)
#
# list[Token] → list[Stmt] (AST)
#
# TDD 진행 상황: 현재 테스트(산술/우선순위)를 통과하는 범위만 구현됨.
#   지원: print 문, 숫자 리터럴, + - * /, 단항 -, 괄호
#   미지원 (다음 테스트가 추가되면 구현): var, if, for, 블록, 대입, 비교, 논리
#
# 문법 (지원 범위, 우선순위 낮음 → 높음):
#   statement → "print" expression ";"
#   expression → term
#   term      → factor ( ( "+" | "-" ) factor )*     ← 덧셈/뺄셈
#   factor    → unary ( ( "*" | "/" ) unary )*       ← 곱셈/나눗셈 (더 깊음 = 먼저 계산)
#   unary     → "-" unary | primary                  ← 단항 마이너스
#   primary   → NUMBER | "(" expression ")"

from ast_nodes import (
    Expr, Stmt,
    LiteralExpr, BinaryExpr, UnaryExpr, GroupingExpr,
    PrintStmt,
)
from tokens import Token, TokenType


class ParseError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._current = 0

    def parse(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self._is_at_end():
            statements.append(self._statement())
        return statements

    # ── Statement 파싱 ─────────────────────────────────────
    def _statement(self) -> Stmt:
        if self._match(TokenType.PRINT):
            return self._print_statement()
        raise ParseError(self._peek().line, "지원하지 않는 문장입니다.")

    def _print_statement(self) -> PrintStmt:
        value = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return PrintStmt(value)

    # ── Expression 파싱 (우선순위 낮음 → 높음) ──────────────
    def _expression(self) -> Expr:
        return self._term()

    def _term(self) -> Expr:  # + -
        # 왼쪽부터 묶는다: 10 - 4 - 3 → (10 - 4) - 3
        expr = self._factor()  #
        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous()
            right = self._factor()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _factor(self) -> Expr:
        expr = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH):
            operator = self._previous()
            right = self._unary()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.MINUS):
            return UnaryExpr(self._previous(), self._unary())
        return self._primary()

    def _primary(self) -> Expr:
        if self._match(TokenType.NUMBER):
            return LiteralExpr(self._previous().value)
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
            return GroupingExpr(expr)
        raise ParseError(self._peek().line, "표현식이 필요합니다.")

    # ── 헬퍼 메서드 ──────────────────────────────────────────
    def _match(self, *types: TokenType) -> bool:
        """현재 토큰이 types 중 하나면 소비하고 True"""
        for t in types:
            if self._check(t):
                self._advance()
                return True
        return False

    def _check(self, t: TokenType) -> bool:
        return not self._is_at_end() and self._peek().type == t

    def _advance(self) -> Token:
        if not self._is_at_end():
            self._current += 1
        return self._previous()

    def _consume(self, t: TokenType, msg: str) -> Token:
        """기대한 토큰이면 소비, 아니면 ParseError"""
        if self._check(t):
            return self._advance()
        raise ParseError(self._peek().line, msg)

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF
