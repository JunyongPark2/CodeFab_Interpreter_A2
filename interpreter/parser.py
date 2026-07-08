from collections.abc import Callable

from .ast_nodes import (
    ArrayExpr,
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ClassDeclStmt,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDeclStmt,
    GetExpr,
    GroupingExpr,
    IfStmt,
    ImportStmt,
    IndexGetExpr,
    IndexSetExpr,
    InstanceOfExpr,
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    ReturnStmt,
    SetExpr,
    Stmt,
    SuperExpr,
    ThisExpr,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from .errors import ParseError
from .tokens import Token, TokenType


class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens = tokens
        self._current = 0
        # for 본문을 파싱하는 동안에만 1 이상이 된다 (중첩 for도 재진입 가능하도록 카운터).
        # import는 for 반복문 내부(중첩된 블록/if 포함) 어디서도 금지되므로, 특정 호출
        # 경로에 플래그를 넘기는 대신 파서 전역 상태로 관리하는 게 더 간단하고 안전하다.
        self._import_forbidden_depth = 0
        # 새 구문 추가 시 여기에 항목만 등록하면 됩니다.
        self._stmt_dispatch: dict[TokenType, Callable[[], Stmt]] = {
            TokenType.IF: self._if_statement,
            TokenType.FOR: self._for_statement,
            TokenType.VAR: self._var_declaration,
            TokenType.LEFT_BRACE: self._block_statement,
            TokenType.PRINT: self._print_statement,
            TokenType.FUNC: self._func_declaration,
            TokenType.RETURN: self._return_statement,
            TokenType.IMPORT: self._import_statement,
            TokenType.CLASS: self._class_declaration,
        }

    def parse(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self._is_at_end():
            statements.append(self._statement())
        return statements

    # ── Statement 파싱 ─────────────────────────────────────
    def _statement(self) -> Stmt:
        if self._check(TokenType.IMPORT) and self._import_forbidden_depth > 0:
            raise ParseError(
                self._peek().line, "반복문 내부에서는 import를 사용할 수 없습니다."
            )
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
        then_branch = self._body_statement()
        else_branch = None
        if self._match(TokenType.ELSE):
            else_branch = self._body_statement()
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

        self._import_forbidden_depth += 1
        try:
            body = self._body_statement()
        finally:
            self._import_forbidden_depth -= 1
        return ForStmt(initializer, condition, increment, body)

    def _body_statement(self) -> Stmt:
        """if/for/else의 본문(statement)을 파싱한다.

        여기서 입력이 끝나 있으면(EOF) "본문이 아직 안 왔다"는 뜻이므로
        incomplete=True로 표시해서 REPL이 더 받을 수 있게 한다.
        """
        if self._is_at_end():
            # 마지막으로 읽은 토큰의 줄을 보고한다
            raise ParseError(self._previous().line, "문장이 필요합니다.", incomplete=True)
        return self._statement()

    def _func_declaration(self) -> FuncDeclStmt:
        name = self._consume(TokenType.IDENTIFIER, "함수 이름이 필요합니다.")
        self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")
        params = self._parameters()
        self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
        self._consume(TokenType.LEFT_BRACE, "'{' 가 필요합니다.")
        body = self._block()
        return FuncDeclStmt(name, params, body)

    def _parameters(self) -> list[Token]:
        params: list[Token] = []
        if not self._check(TokenType.RIGHT_PAREN):
            params.append(
                self._consume(TokenType.IDENTIFIER, "파라미터 이름이 필요합니다.")
            )
            while self._match(TokenType.COMMA):
                params.append(
                    self._consume(TokenType.IDENTIFIER, "파라미터 이름이 필요합니다.")
                )
        return params

    def _import_statement(self) -> ImportStmt:
        path = self._consume(
            TokenType.STRING, "import 대상 파일 경로(문자열)가 필요합니다."
        )
        self._consume(TokenType.ALIAS, "'alias' 키워드가 필요합니다.")
        alias = self._consume(TokenType.IDENTIFIER, "alias 이름이 필요합니다.")
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return ImportStmt(path, alias)

    def _return_statement(self) -> ReturnStmt:
        keyword = self._previous()
        value = None
        if not self._check(TokenType.SEMICOLON):
            value = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return ReturnStmt(keyword, value)

    def _class_declaration(self) -> ClassDeclStmt:
        name = self._consume(TokenType.IDENTIFIER, "클래스 이름이 필요합니다.")
        superclass = None
        if self._match(TokenType.COLON):
            sc_tok = self._consume(
                TokenType.IDENTIFIER, "부모 클래스 이름이 필요합니다."
            )
            superclass = VariableExpr(sc_tok)
        self._consume(TokenType.LEFT_BRACE, "'{' 가 필요합니다.")
        methods: list[FuncDeclStmt] = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            self._consume(TokenType.FUNC, "메서드는 'Func' 키워드로 시작해야 합니다.")
            methods.append(self._func_declaration())
        self._consume(TokenType.RIGHT_BRACE, "'}' 가 필요합니다.")
        return ClassDeclStmt(name, superclass, methods)

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
            if isinstance(expr, IndexGetExpr):
                return IndexSetExpr(expr.array, expr.bracket, expr.index, value)
            if isinstance(expr, GetExpr):
                return SetExpr(expr.object, expr.name, value)
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

    def _binary(
        self, ops: tuple[TokenType, ...], next_level: Callable[[], Expr]
    ) -> Expr:
        """이항 연산자 공통 루프. 새 우선순위 레벨은 이 메서드를 호출하는 1줄로 추가됩니다."""
        expr = next_level()
        while self._match(*ops):
            operator = self._previous()
            right = next_level()
            expr = BinaryExpr(expr, operator, right)
        return expr

    def _equality(self) -> Expr:
        return self._binary(
            (TokenType.EQUAL_EQUAL, TokenType.BANG_EQUAL), self._instanceof
        )

    def _instanceof(self) -> Expr:
        expr = self._comparison()
        if self._match(TokenType.INSTANCEOF):
            klass = self._consume(TokenType.IDENTIFIER, "클래스 이름이 필요합니다.")
            return InstanceOfExpr(expr, klass)
        return expr

    def _comparison(self) -> Expr:
        return self._binary(
            (
                TokenType.LESS,
                TokenType.GREATER,
                TokenType.LESS_EQUAL,
                TokenType.GREATER_EQUAL,
            ),
            self._term,
        )

    def _term(self) -> Expr:
        return self._binary((TokenType.PLUS, TokenType.MINUS), self._factor)

    def _factor(self) -> Expr:
        return self._binary((TokenType.STAR, TokenType.SLASH), self._unary)

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            return UnaryExpr(self._previous(), self._unary())
        return self._call()

    def _call(self) -> Expr:
        expr = self._index()
        while True:
            if self._match(TokenType.LEFT_PAREN):
                expr = self._finish_call(expr)
            elif self._match(TokenType.DOT):
                name = self._consume(TokenType.IDENTIFIER, "속성 이름이 필요합니다.")
                expr = GetExpr(expr, name)
            else:
                break
        return expr

    def _finish_call(self, callee: Expr) -> CallExpr:
        arguments: list[Expr] = []
        if not self._check(TokenType.RIGHT_PAREN):
            arguments.append(self._expression())
            while self._match(TokenType.COMMA):
                arguments.append(self._expression())
        paren = self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
        return CallExpr(callee, paren, arguments)

    # ── 정적배열 기능: arr[index] 읽기 (연쇄 인덱싱도 허용) ────
    def _index(self) -> Expr:
        expr = self._primary()
        while self._match(TokenType.LEFT_BRACKET):
            bracket = self._previous()
            index = self._expression()
            self._consume(TokenType.RIGHT_BRACKET, "']' 가 필요합니다.")
            expr = IndexGetExpr(expr, bracket, index)
        return expr

    def _primary(self) -> Expr:
        if self._match(TokenType.NUMBER, TokenType.STRING):
            return LiteralExpr(self._previous().value, self._previous().line)
        if self._match(TokenType.TRUE):
            return LiteralExpr(True, self._previous().line)
        if self._match(TokenType.FALSE):
            return LiteralExpr(False, self._previous().line)
        if self._match(TokenType.THIS):
            return ThisExpr(self._previous())
        if self._match(TokenType.SUPER):
            keyword = self._previous()
            self._consume(TokenType.DOT, "'.' 가 필요합니다.")
            method = self._consume(TokenType.IDENTIFIER, "메서드 이름이 필요합니다.")
            return SuperExpr(keyword, method)
        if self._match(TokenType.IDENTIFIER):
            return VariableExpr(self._previous())
        # 정적배열 기능: Array(size)
        if self._match(TokenType.ARRAY):
            keyword = self._previous()
            self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")
            size = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
            return ArrayExpr(size, keyword)
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
            return GroupingExpr(expr)
        raise ParseError(self._previous().line, "표현식이 필요합니다.")

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
        incomplete = self._is_at_end() and t in (
            TokenType.RIGHT_PAREN,
            TokenType.RIGHT_BRACE,
        )
        # 마지막으로 읽은 토큰(previous)의 줄을 지정
        raise ParseError(self._previous().line, msg, incomplete=incomplete)

    def _peek(self) -> Token:
        return self._tokens[self._current]

    def _previous(self) -> Token:
        return self._tokens[self._current - 1]

    def _is_at_end(self) -> bool:
        return self._peek().type == TokenType.EOF
