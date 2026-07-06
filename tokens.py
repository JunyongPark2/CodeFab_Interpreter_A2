from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # 구분자
    LEFT_PAREN  = auto()   # (
    RIGHT_PAREN = auto()   # )
    LEFT_BRACE  = auto()   # {
    RIGHT_BRACE = auto()   # }
    SEMICOLON   = auto()   # ;
    COMMA       = auto()   # , (필요 시)

    # 산술 연산자
    PLUS  = auto()   # +
    MINUS = auto()   # -
    STAR  = auto()   # *
    SLASH = auto()   # /

    # 비교 / 대입 연산자
    EQUAL         = auto()   # =
    EQUAL_EQUAL   = auto()   # ==
    GREATER       = auto()   # >
    LESS          = auto()   # <
    GREATER_EQUAL = auto()   # >=
    LESS_EQUAL    = auto()   # <=
    BANG          = auto()   # !
    BANG_EQUAL    = auto()   # !=

    # 리터럴
    IDENTIFIER = auto()   # 변수명, 함수명
    STRING     = auto()   # "hello"
    NUMBER     = auto()   # 37, 3.14  (float로 저장)

    # 키워드
    VAR   = auto()   # var
    IF    = auto()   # if
    ELSE  = auto()   # else
    FOR   = auto()   # for
    PRINT = auto()   # print
    TRUE  = auto()   # true
    FALSE = auto()   # false
    AND   = auto()   # and
    OR    = auto()   # or

    EOF = auto()     # 토큰 스트림 끝


# 키워드 문자열 → TokenType 매핑 (Tokenizer에서 사용)
KEYWORDS: dict[str, TokenType] = {
    "var":   TokenType.VAR,
    "if":    TokenType.IF,
    "else":  TokenType.ELSE,
    "for":   TokenType.FOR,
    "print": TokenType.PRINT,
    "true":  TokenType.TRUE,
    "false": TokenType.FALSE,
    "and":   TokenType.AND,
    "or":    TokenType.OR,
}


@dataclass
class Token:
    type: TokenType       # 토큰 종류 (열거형)
    text: str           # 원본 문자열 (예: "37", "if", "age")
    value: Any = None     # 실제 값 (NUMBER → float, STRING → str, 그 외 None)
    line: int = 0         # 소스코드 줄 번호 (오류 메시지 출력용)
    col: int = 0

    def __repr__(self):
        return f"Token({self.type.name}, {self.text}, value={self.value}, line={self.line}, col={self.col})"
