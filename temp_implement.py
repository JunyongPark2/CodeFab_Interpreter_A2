from dataclasses import dataclass
from typing import Any, Optional
from enum import Enum, auto
    # ── Expr, Statements 구현시 삭제 ─────────────────────────────────────────────
class Expr:
    pass

@dataclass
class LiteralExpr(Expr):
    value: Any                  # float | str | bool | None

@dataclass
class VariableExpr(Expr):
    name: "Token"               # Token(IDENTIFIER, "변수명")

@dataclass
class AssignExpr(Expr):
    name: "Token"               # 대입 대상 변수 Token(IDENTIFIER, ...)
    value: Expr                 # 대입할 값 표현식

@dataclass
class BinaryExpr(Expr):
    left: Expr
    operator: "Token"           # PLUS / MINUS / STAR / SLASH / GREATER / LESS ...
    right: Expr

@dataclass
class UnaryExpr(Expr):
    operator: "Token"           # MINUS / BANG
    right: Expr

@dataclass
class GroupingExpr(Expr):
    expression: Expr            # ( 내부 Expr )

@dataclass
class LogicalExpr(Expr):
    left: Expr
    operator: "Token"           # AND / OR
    right: Expr

class Stmt:
    pass

@dataclass
class ExpressionStmt(Stmt):
    expression: Expr            # Expr을 Stmt로 감싸는 Wrapper

@dataclass
class PrintStmt(Stmt):
    expression: Expr            # 출력할 표현식

@dataclass
class VarDeclStmt(Stmt):
    name: "Token"               # 변수 이름 Token(IDENTIFIER, ...)
    initializer: Optional[Expr] # 초기화 식 (없으면 None)

@dataclass
class BlockStmt(Stmt):
    statements: list[Stmt]      # 블록 내 문장 목록

@dataclass
class IfStmt(Stmt):
    condition: Expr
    then_branch: Stmt
    else_branch: Optional[Stmt] # 없으면 None

@dataclass
class ForStmt(Stmt):
    initializer: Optional[Stmt]  # var i = 0; 또는 None
    condition: Optional[Expr]    # i < 3 또는 None (무한루프)
    increment: Optional[Expr]    # i = i + 1 또는 None
    body: Stmt

class Environment:
    def __init__(self, parent: Environment | None = None):
        self._values: dict[str, Any] = {}
        self.parent = parent               # 상위 스코프 (None 이면 Global)

    def define(self, name: str, value: Any) -> None:
        """현재 스코프에 변수 선언 (중복 허용 — Checker가 사전 차단)"""
        self._values[name] = value

    def get(self, name: str) -> Any:
        """현재 → 상위 스코프 순으로 변수 탐색"""
        if name in self._values:
            return self._values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise LangRuntimeError(0, f"미정의된 변수 '{name}'")

    def assign(self, name: str, value: Any) -> None:
        """이미 선언된 변수 재할당 (선언된 스코프에 직접 씀)"""
        if name in self._values:
            self._values[name] = value
            return
        if self.parent is not None:
            self.parent.assign(name, value)
            return
        raise LangRuntimeError(0, f"미정의된 변수 '{name}'")

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


@dataclass
class Token:
    type: TokenType
    origin: Optional[str] = None   # 렉심(lexeme)/변수명 등 원본 문자열
    line: int = 1


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