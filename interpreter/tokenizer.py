from .tokens import KEYWORDS, Token, TokenType


class TokenizeError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")


class Tokenizer:
    def __init__(self, source: str):
        self._source = source
        self._tokens: list[Token] = []
        self._start = 0  # 현재 토큰 시작 위치
        self._current = 0  # 현재 읽는 위치
        self._line = 1  # 현재 줄 번호
        self._col = 1  # 현재 토큰 시작 열 번호

    def tokenize(self) -> list[Token]:
        while not self._is_at_end():
            self._start = self._current
            self._col = self._current - self._line_start() + 1
            self._scan_token()
        self._tokens.append(Token(TokenType.EOF, "", None, self._line, self._col))
        return self._tokens

    def _line_start(self) -> int:
        idx = self._source.rfind("\n", 0, self._current)
        return idx + 1

    def _scan_token(self) -> None:
        c = self._advance()
        match c:
            case "(":
                self._add_token(TokenType.LEFT_PAREN)
            case ")":
                self._add_token(TokenType.RIGHT_PAREN)
            case "{":
                self._add_token(TokenType.LEFT_BRACE)
            case "}":
                self._add_token(TokenType.RIGHT_BRACE)
            case ";":
                self._add_token(TokenType.SEMICOLON)
            case ",":
                self._add_token(TokenType.COMMA)
            case "+":
                self._add_token(TokenType.PLUS)
            case "-":
                self._add_token(TokenType.MINUS)
            case "*":
                self._add_token(TokenType.STAR)
            case "/":
                if self._peek() == "/":  # // 줄 주석 → 줄 끝까지 무시
                    while self._peek() != "\n" and not self._is_at_end():
                        self._advance()
                else:
                    self._add_token(TokenType.SLASH)
            case "=":
                self._add_token(
                    TokenType.EQUAL_EQUAL if self._match_char("=") else TokenType.EQUAL
                )
            case "!":
                self._add_token(
                    TokenType.BANG_EQUAL if self._match_char("=") else TokenType.BANG
                )
            case ">":
                self._add_token(
                    TokenType.GREATER_EQUAL
                    if self._match_char("=")
                    else TokenType.GREATER
                )
            case "<":
                self._add_token(
                    TokenType.LESS_EQUAL if self._match_char("=") else TokenType.LESS
                )
            case " " | "\r" | "\t":
                pass  # 공백 무시
            case "\n":
                self._line += 1
            case '"':
                self._string('"')
            case "'":
                self._string("'")
            case _:
                if c.isdigit():
                    self._number()
                elif c.isalpha() or c == "_":
                    self._identifier()
                else:
                    raise TokenizeError(self._line, f"인식할 수 없는 문자: '{c}'")

    def _identifier(self) -> None:
        while not self._is_at_end() and (self._peek().isalnum() or self._peek() == "_"):
            self._advance()
        origin = self._source[self._start : self._current]
        token_type = KEYWORDS.get(origin, TokenType.IDENTIFIER)
        self._add_token(token_type)

    def _number(self) -> None:
        while not self._is_at_end() and self._peek().isdigit():
            self._advance()
        if (
            not self._is_at_end()
            and self._peek() == "."
            and self._peek_next().isdigit()
        ):
            self._advance()  # '.' 소비
            while not self._is_at_end() and self._peek().isdigit():
                self._advance()
        origin = self._source[self._start : self._current]
        self._add_token(TokenType.NUMBER, float(origin))

    def _string(self, quote: str) -> None:
        while not self._is_at_end() and self._peek() != quote:
            if self._peek() == "\n":
                self._line += 1
            self._advance()
        if self._is_at_end():
            raise TokenizeError(self._line, "문자열이 닫히지 않았습니다.")
        self._advance()  # 닫는 따옴표 소비
        value = self._source[self._start + 1 : self._current - 1]
        self._add_token(TokenType.STRING, value)

    # ── 헬퍼 메서드 ──────────────────────────────────────────
    def _advance(self) -> str:
        ch = self._source[self._current]
        self._current += 1
        return ch

    def _peek(self) -> str:
        return self._source[self._current] if not self._is_at_end() else "\0"

    def _peek_next(self) -> str:
        if self._current + 1 >= len(self._source):
            return "\0"
        return self._source[self._current + 1]

    def _match_char(self, expected: str) -> bool:
        """다음 문자가 expected이면 소비 후 True, 아니면 False"""
        if self._is_at_end() or self._source[self._current] != expected:
            return False
        self._current += 1
        return True

    def _add_token(self, token_type: TokenType, value=None) -> None:
        origin = self._source[self._start : self._current]
        self._tokens.append(Token(token_type, origin, value, self._line, self._col))

    def _is_at_end(self) -> bool:
        return self._current >= len(self._source)
