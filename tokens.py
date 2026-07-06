"""공통 데이터 구조: TokenType, Token, KEYWORDS.

Assembler Unit(Tokenizer/Parser) 팀이 완성할 파일이지만, 인터페이스가
CodeFab_Interpreter_Guide.md 5-1장에 확정되어 있으므로 Checker 개발/테스트를
위해 동일한 스펙으로 미리 작성한다. 실제 Assembler 코드 합류 시 이 파일을 교체한다.
"""
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class TokenType(Enum):
    # 구분자
    LEFT_PAREN = auto()
    RIGHT_PAREN = auto()
    LEFT_BRACE = auto()
    RIGHT_BRACE = auto()
    SEMICOLON = auto()
    COMMA = auto()

    # 산술 연산자
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()

    # 비교 / 대입 연산자
    EQUAL = auto()
    EQUAL_EQUAL = auto()
    GREATER = auto()
    LESS = auto()
    GREATER_EQUAL = auto()
    LESS_EQUAL = auto()
    BANG = auto()
    BANG_EQUAL = auto()

    # 리터럴
    IDENTIFIER = auto()
    STRING = auto()
    NUMBER = auto()

    # 키워드
    VAR = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    PRINT = auto()
    TRUE = auto()
    FALSE = auto()
    AND = auto()
    OR = auto()

    EOF = auto()


KEYWORDS: dict[str, TokenType] = {
    "var": TokenType.VAR,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "print": TokenType.PRINT,
    "true": TokenType.TRUE,
    "false": TokenType.FALSE,
    "and": TokenType.AND,
    "or": TokenType.OR,
}


@dataclass
class Token:
    type: TokenType
    origin: str
    value: Any = None
    line: int = 0

    def __repr__(self):
        return f"Token({self.type.name}, {self.origin!r}, value={self.value})"
