# parser.py — Parser, ParseError
#
# list[Token] → list[Stmt] (AST)
#
# 문법 (우선순위 낮음 → 높음):
#   program    → statement* EOF
#   statement  → varDecl | ifStmt | forStmt | block | printStmt | exprStmt
#   varDecl    → "var" IDENTIFIER "=" expression ";"
#   ifStmt     → "if" "(" expression ")" statement ( "else" statement )?
#   forStmt    → "for" "(" ( varDecl | exprStmt | ";" ) expression? ";" expression? ")" statement
#   block      → "{" statement* "}"
#   printStmt  → "print" expression ";"
#   exprStmt   → expression ";"
#   expression → assignment
#   assignment → IDENTIFIER "=" assignment | logic_or
#   logic_or   → logic_and ( "or" logic_and )*
#   logic_and  → equality ( "and" equality )*
#   equality   → comparison ( ( "==" | "!=" ) comparison )*
#   comparison → term ( ( "<" | ">" | "<=" | ">=" ) term )*
#   term       → factor ( ( "+" | "-" ) factor )*
#   factor     → unary ( ( "*" | "/" ) unary )*
#   unary      → ( "!" | "-" ) unary | primary
#   primary    → NUMBER | STRING | "true" | "false" | IDENTIFIER | "(" expression ")"

from collections.abc import Callable

from .ast_nodes import (
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    Expr,
    ExpressionStmt,
    ForStmt,
    GroupingExpr,
    IfStmt,
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    Stmt,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from .tokens import Token, TokenType


class ParseError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._current = 0
        # 새 구문 추가 시 여기에 항목만 등록하면 됩니다.
        self._stmt_dispatch: dict[TokenType, Callable[[], Stmt]] = {
            TokenType.IF: self._if_statement,
            TokenType.FOR: self._for_statement,
            TokenType.VAR: self._var_declaration,
            TokenType.LEFT_BRACE: self._block_statement,
            TokenType.PRINT: self._print_statement,
        }

    def parse(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self._is_at_end():
            statements.append(self._statement())
        return statements

    # ── Statement 파싱 ─────────────────────────────────────
    def _statement(self) -> Stmt:
        for token_type, handler in self._stmt_dispatch.items():
            if self._match(token_type):
                return handler()
        return self._expression_statement()

    def _block_statement(self) -> BlockStmt:
        return BlockStmt(self._block())

    def _if_statement(self) -> IfStmt:
        self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
        then_branch = self._statement()
        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._statement()
        return IfStmt(condition, then_branch, else_branch)

    def _for_statement(self) -> ForStmt:
        self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")

        if self._match(TokenType.SEMICOLON):
            initializer = None
        elif self._match(TokenType.VAR):
            initializer = self._var_declaration()
        else:
            initializer = self._expression_statement()

        condition = None
        if not self._check(TokenType.SEMICOLON):
            condition = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")

        increment = None
        if not self._check(TokenType.RIGHT_PAREN):
            increment = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")

        body = self._statement()
        return ForStmt(initializer, condition, increment, body)

    def _var_declaration(self) -> VarDeclStmt:
        name = self._consume(TokenType.IDENTIFIER, "변수 이름이 필요합니다.")
        initializer = None
        if self._match(TokenType.EQUAL):
            initializer = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return VarDeclStmt(name, initializer)

    def _block(self) -> list[Stmt]:
        """LEFT_BRACE 를 소비한 뒤 호출. RIGHT_BRACE 까지 문장을 수집한다."""
        statements: list[Stmt] = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            statements.append(self._statement())
        self._consume(TokenType.RIGHT_BRACE, "'}' 가 필요합니다.")
        return statements

    def _print_statement(self) -> PrintStmt:
        value = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return PrintStmt(value)

    def _expression_statement(self) -> ExpressionStmt:
        expr = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return ExpressionStmt(expr)

    # ── Expression 파싱 (우선순위 낮음 → 높음) ──────────────
    def _expression(self) -> Expr:
        return self._assignment()

    def _assignment(self) -> Expr:
        expr = self._logic_or()
        if self._match(TokenType.EQUAL):
            value = self._assignment()  # 오른쪽 결합: a = b = 1
            if isinstance(expr, VariableExpr):
                return AssignExpr(expr.name, value)
            raise ParseError(self._previous().line, "대입 대상이 올바르지 않습니다.")
        return expr

    def _logic_or(self) -> Expr:
        expr = self._logic_and()
        while self._match(TokenType.OR):
            op = self._previous()
            right = self._logic_and()
            expr = LogicalExpr(expr, op, right)
        return expr

    def _logic_and(self) -> Expr:
        expr = self._equality()
        while self._match(TokenType.AND):
            op = self._previous()
            right = self._equality()
            expr = LogicalExpr(expr, op, right)
        return expr

    def _binary(self, ops: tuple[TokenType, ...], next_level: Callable[[], Expr]) -> Expr:
        """이항 연산자 공통 루프. 새 우선순위 레벨은 이 메서드를 호출하는 1줄로 추가됩니다."""
        expr = next_level()
        while self._match(*ops):
            operator = self._previous()
            right = next_level()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _equality(self) -> Expr:
        return self._binary((TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL), self._comparison)

    def _comparison(self) -> Expr:
        return self._binary(
            (TokenType.LESS, TokenType.GREATER, TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL),
            self._term,
        )

    def _term(self) -> Expr:
        return self._binary((TokenType.PLUS, TokenType.MINUS), self._factor)

    def _factor(self) -> Expr:
        return self._binary((TokenType.STAR, TokenType.SLASH), self._unary)

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            return UnaryExpr(self._previous(), self._unary())
        return self._primary()

    def _primary(self) -> Expr:
        if self._match(TokenType.NUMBER, TokenType.STRING):
            return LiteralExpr(self._previous().value)
        if self._match(TokenType.TRUE):
            return LiteralExpr(True)
        if self._match(TokenType.FALSE):
            return LiteralExpr(False)
        if self._match(TokenType.IDENTIFIER):
            return VariableExpr(self._previous())
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
        if self._check(t):
            return self._advance()
        raise ParseError(self._peek().line, msg)

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF
