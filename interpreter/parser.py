# parser.py — Parser, ParseError (박준용, 송지영)
#
# list[Token] → list[Stmt] (AST)
#
# 문법 (우선순위 낮음 → 높음):
#   program    → statement* EOF
#   statement  → varDecl | block | printStmt | exprStmt
#   varDecl    → "var" IDENTIFIER "=" expression ";"
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

from .ast_nodes import (
    Expr, Stmt,
    LiteralExpr, BinaryExpr, UnaryExpr, GroupingExpr,
    VariableExpr, AssignExpr, LogicalExpr,
    PrintStmt, ExpressionStmt, VarDeclStmt, BlockStmt,
    IfStmt, ForStmt,
)
from .tokens import Token, TokenType


class ParseError(Exception):
    def __init__(self, line: int, msg: str, incomplete: bool = False):
        # incomplete: "더 입력하면 완성될 수 있는" 실패인지 여부. 아래 두
        # 경우에만 True가 된다 (REPL이 "다음 줄을 더 받아야 한다"와 "진짜
        # 문법 오류"를 구분할 때 쓴다. prompt_shell.py 참고):
        #   1) if/for/else의 본문(statement) 자리에 아무 토큰도 없이(EOF) 실패
        #   2) ')' / '}' 가 필요한 자리에서, 다른 토큰이 아니라 EOF라서 실패
        #      (예: "print (1+2"는 True, "print (1+2;"는 세미콜론이 이미
        #      와버렸으니 False — 더 받아도 절대 고쳐지지 않는 진짜 에러)
        # 세미콜론 누락이나 연산자만 남은 식처럼 그 외의 이유로 EOF에서
        # 실패한 경우는 여기 해당하지 않는다 — 더 받아도 고쳐지지 않으므로
        # 즉시 에러로 처리해야 한다.
        self.incomplete = incomplete
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
        if self._match(TokenType.IF):
            return self._if_statement()
        if self._match(TokenType.FOR):
            return self._for_statement()
        if self._match(TokenType.VAR):
            return self._var_declaration()
        if self._match(TokenType.LEFT_BRACE):
            return BlockStmt(self._block())
        if self._match(TokenType.PRINT):
            return self._print_statement()
        return self._expression_statement()

    def _if_statement(self) -> IfStmt:
        self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
        then_branch = self._body_statement()
        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._body_statement()
        return IfStmt(condition, then_branch, else_branch)

    def _for_statement(self) -> ForStmt:
        self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")

        # initializer: var 선언 | 식 문장 | 없음(;)
        if self._match(TokenType.SEMICOLON):
            initializer = None
        elif self._match(TokenType.VAR):
            initializer = self._var_declaration()
        else:
            initializer = self._expression_statement()

        # condition
        condition = None
        if not self._check(TokenType.SEMICOLON):
            condition = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")

        # increment
        increment = None
        if not self._check(TokenType.RIGHT_PAREN):
            increment = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")

        body = self._body_statement()
        return ForStmt(initializer, condition, increment, body)

    def _body_statement(self) -> Stmt:
        """if/for/else의 본문(statement)을 파싱한다.

        여기서 입력이 끝나 있으면(EOF) "본문이 아직 안 왔다"는 뜻이므로
        incomplete=True로 표시해서 REPL이 더 받을 수 있게 한다.
        """
        if self._is_at_end():
            raise ParseError(self._peek().line, "문장이 필요합니다.", incomplete=True)
        return self._statement()

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

    def _equality(self) -> Expr:  # == !=
        expr = self._comparison()
        while self._match(TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL):
            operator = self._previous()
            right = self._comparison()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _comparison(self) -> Expr:  # < > <= >=
        expr = self._term()
        while self._match(
                TokenType.LESS, TokenType.GREATER,
                TokenType.LESS_EQUAL, TokenType.GREATER_EQUAL,
        ):
            operator = self._previous()
            right = self._term()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _term(self) -> Expr:  # + -
        expr = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            operator = self._previous()
            right = self._factor()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _factor(self) -> Expr:  # * /
        expr = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH):
            operator = self._previous()
            right = self._unary()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            return UnaryExpr(self._previous(), self._unary())
        return self._primary()

    def _primary(self) -> Expr:
        if self._match(TokenType.NUMBER):
            return LiteralExpr(self._previous().value)
        if self._match(TokenType.STRING):
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
        # ')' / '}' 를 기대했는데 다른 토큰이 아니라 EOF라서 못 찾은 거면
        # "더 입력하면 닫힐 수 있다"는 뜻이므로 incomplete=True.
        # (SEMICOLON 등 다른 토큰을 기대하다 EOF를 만난 경우는 해당 없음 —
        # 세미콜론은 다음 줄에 따로 이어붙일 거라고 보기 어렵기 때문.)
        incomplete = self._is_at_end() and t in (TokenType.RIGHT_PAREN, TokenType.RIGHT_BRACE)
        raise ParseError(self._peek().line, msg, incomplete=incomplete)

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF
