# CodeFab Interpreter 프로젝트 가이드

> **LangFactory** — 팀 전용 Custom 프로그래밍 언어 + 인터프리터 제작 프로젝트  
> **구현 언어: Python**

---

## 목차

1. [프로젝트 개요](#1-프로젝트-개요)
2. [전체 파이프라인 구조](#2-전체-파이프라인-구조)
3. [팀 역할 분담 및 담당자](#3-팀-역할-분담-및-담당자)
4. [모듈 간 Input/Output 인터페이스 명세](#4-모듈-간-inputoutput-인터페이스-명세)
5. [공통 데이터 구조 정의](#5-공통-데이터-구조-정의)
6. [모듈별 상세 구현 가이드](#6-모듈별-상세-구현-가이드)
   - [6-1. Tokenizer (Lexer)](#6-1-tokenizer-lexer--김종화-이채연)
   - [6-2. Parser (문법 트리)](#6-2-parser-문법-트리--박준용-송지영)
   - [6-3. Checker](#6-3-checker--권은재)
   - [6-4. Executor](#6-4-executor--조재현)
7. [Token 타입 전체 목록](#7-token-타입-전체-목록)
8. [Expr 노드 전체 목록](#8-expr-노드-전체-목록)
9. [Stmt 노드 전체 목록](#9-stmt-노드-전체-목록)
10. [예시 스크립트 및 실행 흐름](#10-예시-스크립트-및-실행-흐름)
11. [오류 처리 명세](#11-오류-처리-명세)
12. [개발 일정 및 규칙](#12-개발-일정-및-규칙)

---

## 1. 프로젝트 개요

**CodeFab (Code Fabrication)**은 마치 파이프라인을 갖춘 공장처럼 동작하는 **인터프리터**다.

- 팀 전용 Custom 프로그래밍 언어를 설계한다.
- 그 언어를 실행하는 인터프리터(CodeFab)를 직접 구현한다.
- CLI 기반 Prompt Shell을 제작하여 한 줄 입력 → 즉시 실행이 가능하게 한다.

```
스크립트 입력 → [ CodeFab Interpreter ] → 실행 결과 출력
```

---

## 2. 전체 파이프라인 구조

```
사용자 입력 (소스코드 문자열)
        │
        ▼
┌──────────────────┐
│  Assembler Unit  │
│                  │
│  ┌────────────┐  │
│  │ Tokenizer  │  │  ← 소스코드 → list[Token]
│  └─────┬──────┘  │
│        │         │
│  ┌─────▼──────┐  │
│  │   Parser   │  │  ← list[Token] → list[Stmt] (AST)
│  └────────────┘  │
└────────┬─────────┘
         │  list[Stmt] (AST)
         ▼
┌──────────────────┐
│  Checker Unit    │  ← AST 의미 오류 검사 (중복 선언, 자기 참조 등)
└────────┬─────────┘
         │  list[Stmt] (검증 완료된 AST)
         ▼
┌──────────────────┐
│  Executor Unit   │  ← AST DFS 순회 → 실제 실행 → 출력
└──────────────────┘
```

한 줄 입력이 들어올 때마다 **세 Unit 공정이 모두 순서대로 수행**된다.

---

## 3. 팀 역할 분담 및 담당자

| 모듈 | 역할 | 담당자 |
|------|------|--------|
| **Tokenizer** (Lexer) | 소스코드 문자열 → `list[Token]` 생성 | 김종화, 이채연 |
| **Parser** (문법 트리) | `list[Token]` → `list[Stmt]` (AST) 생성 | 박준용, 송지영 |
| **Checker** | AST 의미 오류 검사 | 권은재 |
| **Executor** | AST 실행 및 결과 출력 | 조재현 |

---

## 4. 모듈 간 Input/Output 인터페이스 명세

> **주의:** 아래 인터페이스는 팀 전원이 반드시 준수해야 한다. 변경 필요 시 팀 전체 합의 후 이 문서를 수정한다.

---

### 4-1. Tokenizer Interface

```
Input  : str                        # 소스코드 전체 문자열 (한 줄 또는 여러 줄)
Output : list[Token]                # Token 객체 목록. 마지막은 반드시 Token(TokenType.EOF, "")
Error  : TokenizeError              # 인식 불가 문자 등 Lexical 오류 발생 시 raise
```

**출력 예시:**
```
입력: "age = 37"
출력: [
  Token(IDENTIFIER, "age"),
  Token(EQUAL, "="),
  Token(NUMBER, "37", value=37.0),
  Token(EOF, "")
]

입력: "if ( x > 10 )"
출력: [
  Token(IF, "if"),
  Token(LEFT_PAREN, "("),
  Token(IDENTIFIER, "x"),
  Token(GREATER, ">"),
  Token(NUMBER, "10", value=10.0),
  Token(RIGHT_PAREN, ")"),
  Token(EOF, "")
]
```

**Token 클래스 구조:**
```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class Token:
    type: TokenType       # 토큰 종류 (열거형)
    origin: str           # 원본 문자열 (예: "37", "if", "age")
    value: Any = None     # 실제 값 (NUMBER → float, STRING → str, 그 외 None)
    line: int = 0         # 소스코드 줄 번호 (오류 메시지 출력용)

    def __repr__(self):
        return f"Token({self.type.name}, {self.origin!r}, value={self.value})"
```

---

### 4-2. Parser Interface

```
Input  : list[Token]                # Tokenizer가 생성한 Token 목록
Output : list[Stmt]                 # AST의 루트 Stmt 목록 (프로그램 전체 문장들)
Error  : ParseError                 # 문법 오류 발생 시 raise (예: 세미콜론 누락, 우항 없음)
```

**출력 예시:**
```
입력: [ Token(VAR,"var"), Token(IDENTIFIER,"a"), Token(EQUAL,"="),
        Token(NUMBER,"3", value=3.0), Token(SEMICOLON,";"), Token(EOF,"") ]

출력: [
  VarDeclStmt(
    name=Token(IDENTIFIER, "a"),
    initializer=LiteralExpr(value=3.0)
  )
]
```

**트리 구성 규칙:**
- 루트(최상위)는 항상 `Stmt`
- `Expr` 내부에 `Stmt`를 Child로 갖는 것은 금지
- `Token`은 노드가 아니라 각 노드의 필드로 보관
- EOF 토큰 도달 시 파싱 종료

---

### 4-3. Checker Interface

```
Input  : list[Stmt]                 # Parser가 생성한 AST
Output : None                       # 오류 없으면 정상 반환
Error  : CheckError                 # 의미 오류 발견 시 raise
           - 같은 블록 내 변수 중복 선언
           - 변수 초기화 식에서 자기 자신 참조
```

**Checker는 AST를 수정하지 않는다.** 오류 없으면 그대로 Executor로 전달.
(1~2일차 기준. 3~4일차 "실행 전 최적화" 기능부터는 이 제약이 완화된다 — 상수 폴딩을 위해
Checker가 리터럴 하위 트리를 `LiteralExpr`로 치환할 수 있고, `check()`의 반환값도
`None`에서 정적 바인딩 결과(`dict[int, int]`, 표현식 id → 스코프 거리)로 바뀐다.
자세한 내용은 `CodeFab_Interpreter_Extension_Guide.md` 4-4장 및 5-4장 참고.)

---

### 4-4. Executor Interface

```
Input  : list[Stmt]                 # Checker를 통과한 AST
Output : None                       # 실행 결과는 stdout에 직접 출력 (print 사용)
Error  : RuntimeError               # 실행 중 오류 발생 시 raise
           - 타입 불일치 연산
           - 미정의 변수 참조
           - 0으로 나누기
```

**Executor가 관리하는 내부 상태:**
- `Environment` (변수 저장소): Global + 블록별 Local로 구성된 체인 구조

---

### 4-5. 전체 파이프라인 연결 (Main / PromptShell 담당)

```python
# prompt_shell.py — PromptShell 진입점 예시

from tokenizer import Tokenizer, TokenizeError
from parser import Parser, ParseError
from checker import Checker, CheckError
from executor import Executor, LangRuntimeError

def run(source: str) -> None:
    try:
        tokens = Tokenizer(source).tokenize()   # Tokenizer
        ast    = Parser(tokens).parse()         # Parser
        Checker(ast).check()                    # Checker
        Executor(ast).execute()                 # Executor
    except (TokenizeError, ParseError, CheckError, LangRuntimeError) as e:
        print(e)

if __name__ == "__main__":
    while True:
        try:
            source = input(">> ")
        except EOFError:
            break
        run(source)
```

---

## 5. 공통 데이터 구조 정의

> 모든 팀원이 동일한 구조를 사용해야 한다.  
> 파일은 `tokens.py`, `ast_nodes.py`, `environment.py` 세 파일로 분리하는 것을 권장한다.

### 5-1. TokenType 열거형 (`tokens.py`)

```python
from enum import Enum, auto

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
```

### 5-2. Expr 노드 (`ast_nodes.py`)

```python
from dataclasses import dataclass
from typing import Any, Optional

# ── 모든 Expr의 공통 부모 ──────────────────────────────────────
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
```

### 5-3. Stmt 노드 (`ast_nodes.py` 이어서)

```python
# ── 모든 Stmt의 공통 부모 ──────────────────────────────────────
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
```

### 5-4. Environment (`environment.py`)

```python
from __future__ import annotations
from typing import Any

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
```

---

## 6. 모듈별 상세 구현 가이드

### 6-1. Tokenizer (Lexer) — 김종화, 이채연

**역할:** 소스코드 문자열을 읽어 의미 있는 최소 단위인 Token으로 분해한다.

**동작 3단계:**

| 단계 | 설명 | 예시 |
|------|------|------|
| 1. 문자 읽기 | 소스코드를 한 문자씩 읽음 | `"age"` 읽기 |
| 2. 패턴 인식 | 문자 패턴으로 종류 판별 | `age` → `IDENTIFIER` |
| 3. 토큰화 | Token 객체 생성하여 목록에 추가 | `Token(IDENTIFIER, "age")` 생성 |

**구현 체크리스트:**
- [ ] 알파벳으로 시작하는 식별자 인식 (`a`, `calcSum`, `isExist`)
- [ ] 숫자 리터럴 인식 (정수 및 실수 → `float`로 변환)
- [ ] 문자열 리터럴 인식 (`"hello"` — 큰따옴표 내부)
- [ ] 단일 문자 연산자/구분자 인식 (`+`, `-`, `*`, `/`, `=`, `>`, `<`, `;`, `(`, `)`, `{`, `}`)
- [ ] 2자 연산자 인식 (`==`, `!=`, `>=`, `<=`)
- [ ] `//` 줄 주석 처리 (해당 줄 끝까지 무시)
- [ ] 키워드 판별 (식별자로 읽은 뒤 `KEYWORDS` 딕셔너리에서 조회)
- [ ] `and`, `or`, `true`, `false` 키워드 처리
- [ ] 공백(space, tab, newline) 무시
- [ ] 줄 번호(`line`) 추적 (오류 메시지용)
- [ ] 인식 불가 문자 → `TokenizeError` raise
- [ ] 마지막에 `Token(TokenType.EOF, "")` 추가

**Tokenizer 구현 스켈레톤:**
```python
# tokenizer.py
from tokens import Token, TokenType, KEYWORDS

class TokenizeError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")

class Tokenizer:
    def __init__(self, source: str):
        self._source  = source
        self._tokens: list[Token] = []
        self._start   = 0    # 현재 토큰 시작 위치
        self._current = 0    # 현재 읽는 위치
        self._line    = 1    # 현재 줄 번호

    def tokenize(self) -> list[Token]:
        while not self._is_at_end():
            self._start = self._current
            self._scan_token()
        self._tokens.append(Token(TokenType.EOF, "", None, self._line))
        return self._tokens

    def _scan_token(self) -> None:
        c = self._advance()
        match c:
            case '(': self._add_token(TokenType.LEFT_PAREN)
            case ')': self._add_token(TokenType.RIGHT_PAREN)
            case '{': self._add_token(TokenType.LEFT_BRACE)
            case '}': self._add_token(TokenType.RIGHT_BRACE)
            case ';': self._add_token(TokenType.SEMICOLON)
            case '+': self._add_token(TokenType.PLUS)
            case '-': self._add_token(TokenType.MINUS)
            case '*': self._add_token(TokenType.STAR)
            case '/':
                if self._peek() == '/':      # // 줄 주석 → 줄 끝까지 무시
                    while self._peek() != '\n' and not self._is_at_end():
                        self._advance()
                else:
                    self._add_token(TokenType.SLASH)
            case '=':
                self._add_token(TokenType.EQUAL_EQUAL if self._match_char('=') else TokenType.EQUAL)
            case '!':
                self._add_token(TokenType.BANG_EQUAL if self._match_char('=') else TokenType.BANG)
            case '>':
                self._add_token(TokenType.GREATER_EQUAL if self._match_char('=') else TokenType.GREATER)
            case '<':
                self._add_token(TokenType.LESS_EQUAL if self._match_char('=') else TokenType.LESS)
            case ' ' | '\r' | '\t': pass   # 공백 무시
            case '\n': self._line += 1
            case '"': self._string()
            case _:
                if c.isdigit():
                    self._number()
                elif c.isalpha() or c == '_':
                    self._identifier()
                else:
                    raise TokenizeError(self._line, f"인식할 수 없는 문자: '{c}'")

    def _identifier(self) -> None:
        while not self._is_at_end() and (self._peek().isalnum() or self._peek() == '_'):
            self._advance()
        text = self._source[self._start:self._current]
        token_type = KEYWORDS.get(text, TokenType.IDENTIFIER)
        self._add_token(token_type)

    def _number(self) -> None:
        while not self._is_at_end() and self._peek().isdigit():
            self._advance()
        if not self._is_at_end() and self._peek() == '.' and self._peek_next().isdigit():
            self._advance()  # '.' 소비
            while not self._is_at_end() and self._peek().isdigit():
                self._advance()
        text = self._source[self._start:self._current]
        self._add_token(TokenType.NUMBER, float(text))

    def _string(self) -> None:
        while not self._is_at_end() and self._peek() != '"':
            if self._peek() == '\n':
                self._line += 1
            self._advance()
        if self._is_at_end():
            raise TokenizeError(self._line, "문자열이 닫히지 않았습니다.")
        self._advance()  # 닫는 " 소비
        value = self._source[self._start + 1:self._current - 1]
        self._add_token(TokenType.STRING, value)

    # ── 헬퍼 메서드 ──────────────────────────────────────────
    def _advance(self) -> str:
        ch = self._source[self._current]
        self._current += 1
        return ch

    def _peek(self) -> str:
        return self._source[self._current] if not self._is_at_end() else '\0'

    def _peek_next(self) -> str:
        if self._current + 1 >= len(self._source):
            return '\0'
        return self._source[self._current + 1]

    def _match_char(self, expected: str) -> bool:
        """다음 문자가 expected이면 소비 후 True, 아니면 False"""
        if self._is_at_end() or self._source[self._current] != expected:
            return False
        self._current += 1
        return True

    def _add_token(self, token_type: TokenType, value=None) -> None:
        text = self._source[self._start:self._current]
        self._tokens.append(Token(token_type, text, value, self._line))

    def _is_at_end(self) -> bool:
        return self._current >= len(self._source)
```

---

### 6-2. Parser (문법 트리) — 박준용, 송지영

**역할:** Token List를 소비하며 문법 규칙에 따라 AST(Abstract Syntax Tree)를 구성한다.

**문법 규칙 (BNF 형식):**

```
program       → statement* EOF

statement     → varDecl
              | printStmt
              | ifStmt
              | forStmt
              | block
              | exprStmt

varDecl       → "var" IDENTIFIER ( "=" expression )? ";"
printStmt     → "print" expression ";"
ifStmt        → "if" "(" expression ")" statement ( "else" statement )?
forStmt       → "for" "(" ( varDecl | exprStmt | ";" )
                           expression? ";"
                           expression? ")" statement
block         → "{" statement* "}"
exprStmt      → expression ";"

expression    → assignment
assignment    → IDENTIFIER "=" assignment | logic_or
logic_or      → logic_and ( "or" logic_and )*
logic_and     → equality ( "and" equality )*
equality      → comparison ( ( "==" | "!=" ) comparison )*
comparison    → term ( ( ">" | ">=" | "<" | "<=" ) term )*
term          → factor ( ( "+" | "-" ) factor )*
factor        → unary ( ( "*" | "/" ) unary )*
unary         → ( "!" | "-" ) unary | primary
primary       → NUMBER | STRING | "true" | "false"
              | IDENTIFIER | "(" expression ")"
```

**파싱 우선순위 (낮음 → 높음):**
```
assignment  <  logic_or  <  logic_and  <  equality  <  comparison
<  term(+-)  <  factor(*/)  <  unary(!-)  <  primary
```

**Parser 구현 스켈레톤:**
```python
# parser.py
from tokens import Token, TokenType
from ast_nodes import *

class ParseError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")

class Parser:
    def __init__(self, tokens: list[Token]):
        self._tokens  = tokens
        self._current = 0

    def parse(self) -> list[Stmt]:
        statements: list[Stmt] = []
        while not self._is_at_end():
            statements.append(self._declaration())
        return statements

    # ── Statement 파싱 ─────────────────────────────────────
    def _declaration(self) -> Stmt:
        if self._match(TokenType.VAR):
            return self._var_declaration()
        return self._statement()

    def _statement(self) -> Stmt:
        if self._match(TokenType.PRINT):      return self._print_statement()
        if self._match(TokenType.IF):         return self._if_statement()
        if self._match(TokenType.FOR):        return self._for_statement()
        if self._match(TokenType.LEFT_BRACE): return BlockStmt(self._block())
        return self._expression_statement()

    def _var_declaration(self) -> VarDeclStmt:
        name = self._consume(TokenType.IDENTIFIER, "변수 이름이 필요합니다.")
        initializer = None
        if self._match(TokenType.EQUAL):
            initializer = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return VarDeclStmt(name, initializer)

    def _print_statement(self) -> PrintStmt:
        value = self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        return PrintStmt(value)

    def _if_statement(self) -> IfStmt:
        self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")
        condition = self._expression()
        self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
        then_branch = self._statement()
        else_branch = self._statement() if self._match(TokenType.ELSE) else None
        return IfStmt(condition, then_branch, else_branch)

    def _for_statement(self) -> Stmt:
        self._consume(TokenType.LEFT_PAREN, "'(' 가 필요합니다.")
        if self._match(TokenType.VAR):
            initializer = self._var_declaration()
        elif self._match(TokenType.SEMICOLON):
            initializer = None
        else:
            initializer = self._expression_statement()
        condition = None if self._check(TokenType.SEMICOLON) else self._expression()
        self._consume(TokenType.SEMICOLON, "';' 가 필요합니다.")
        increment = None if self._check(TokenType.RIGHT_PAREN) else self._expression()
        self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
        body = self._statement()
        return ForStmt(initializer, condition, increment, body)

    def _block(self) -> list[Stmt]:
        stmts: list[Stmt] = []
        while not self._check(TokenType.RIGHT_BRACE) and not self._is_at_end():
            stmts.append(self._declaration())
        self._consume(TokenType.RIGHT_BRACE, "'}' 가 필요합니다.")
        return stmts

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
            value = self._assignment()
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

    def _equality(self) -> Expr:
        expr = self._comparison()
        while self._match(TokenType.BANG_EQUAL, TokenType.EQUAL_EQUAL):
            expr = BinaryExpr(expr, self._previous(), self._comparison())
        return expr

    def _comparison(self) -> Expr:
        expr = self._term()
        while self._match(TokenType.GREATER, TokenType.GREATER_EQUAL,
                          TokenType.LESS, TokenType.LESS_EQUAL):
            expr = BinaryExpr(expr, self._previous(), self._term())
        return expr

    def _term(self) -> Expr:
        expr = self._factor()
        while self._match(TokenType.PLUS, TokenType.MINUS):
            expr = BinaryExpr(expr, self._previous(), self._factor())
        return expr

    def _factor(self) -> Expr:
        expr = self._unary()
        while self._match(TokenType.STAR, TokenType.SLASH):
            expr = BinaryExpr(expr, self._previous(), self._unary())
        return expr

    def _unary(self) -> Expr:
        if self._match(TokenType.BANG, TokenType.MINUS):
            return UnaryExpr(self._previous(), self._unary())
        return self._primary()

    def _primary(self) -> Expr:
        if self._match(TokenType.FALSE):      return LiteralExpr(False)
        if self._match(TokenType.TRUE):       return LiteralExpr(True)
        if self._match(TokenType.NUMBER, TokenType.STRING):
            return LiteralExpr(self._previous().value)
        if self._match(TokenType.IDENTIFIER): return VariableExpr(self._previous())
        if self._match(TokenType.LEFT_PAREN):
            expr = self._expression()
            self._consume(TokenType.RIGHT_PAREN, "')' 가 필요합니다.")
            return GroupingExpr(expr)
        raise ParseError(self._peek().line, "표현식이 필요합니다.")

    # ── 헬퍼 메서드 ──────────────────────────────────────────
    def _match(self, *types: TokenType) -> bool:
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

    def _peek(self) -> Token:     return self._tokens[self._current]
    def _previous(self) -> Token: return self._tokens[self._current - 1]
    def _is_at_end(self) -> bool: return self._peek().type == TokenType.EOF
```

**문법 트리 구성 규칙:**
- 루트는 항상 `Stmt`
- `Expr` 내부에 `Stmt` Child 불가
- `=`, `;` 등 실행에 불필요한 토큰은 노드로 만들지 않음 (필드에 보관)
- 연산자 우선순위는 트리 깊이로 표현됨 (깊을수록 먼저 평가)

**우선순위 트리 예시:**
```
a + b * 3

BinaryExpr(+)
├── VariableExpr(a)
└── BinaryExpr(*)       ← * 가 + 보다 깊음 → 먼저 실행
    ├── VariableExpr(b)
    └── LiteralExpr(3)
```

---

### 6-3. Checker — 권은재

**역할:** AST를 DFS(깊이 우선 탐색)로 순회하며 의미적 오류를 사전에 검출한다. (런타임 전 정적 분석)

**검사 항목:**

#### (1) 같은 블록 내 변수 중복 선언
```
{
    var a = "first";
    var a = "second";  # Error: 같은 블록에 'a' 이미 선언됨
}
```

#### (2) 변수 초기화 식에서 자기 자신 참조
```
{
    var a = a + 1;  # Error: 초기화 식에서 지역변수 'a' 를 읽을 수 없음
}
```

**구현 방법 — 스코프 스택:**
```python
# checker.py
from ast_nodes import *

class CheckError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")

class Checker:
    def __init__(self, stmts: list[Stmt]):
        self._stmts = stmts
        # 스코프 스택: 각 스코프는 { 변수명: 초기화완료여부(bool) } 딕셔너리
        self._scopes: list[dict[str, bool]] = []

    def check(self) -> None:
        for stmt in self._stmts:
            self._check_stmt(stmt)

    # ── Stmt 방문 ─────────────────────────────────────────
    def _check_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, VarDeclStmt):   self._check_var_decl(stmt)
        elif isinstance(stmt, BlockStmt):   self._check_block(stmt)
        elif isinstance(stmt, IfStmt):      self._check_if(stmt)
        elif isinstance(stmt, ForStmt):     self._check_for(stmt)
        elif isinstance(stmt, PrintStmt):   self._check_expr(stmt.expression)
        elif isinstance(stmt, ExpressionStmt): self._check_expr(stmt.expression)

    def _check_var_decl(self, stmt: VarDeclStmt) -> None:
        if self._scopes:
            scope = self._scopes[-1]
            if stmt.name.origin in scope:
                raise CheckError(
                    stmt.name.line,
                    f"변수 '{stmt.name.origin}'이(가) 이미 이 스코프에 선언되어 있습니다."
                )
            scope[stmt.name.origin] = False   # 초기화 미완

        if stmt.initializer is not None:
            self._check_expr(stmt.initializer)

        if self._scopes:
            self._scopes[-1][stmt.name.origin] = True  # 초기화 완료

    def _check_block(self, stmt: BlockStmt) -> None:
        self._begin_scope()
        for s in stmt.statements:
            self._check_stmt(s)
        self._end_scope()

    def _check_if(self, stmt: IfStmt) -> None:
        self._check_expr(stmt.condition)
        self._check_stmt(stmt.then_branch)
        if stmt.else_branch:
            self._check_stmt(stmt.else_branch)

    def _check_for(self, stmt: ForStmt) -> None:
        self._begin_scope()
        if stmt.initializer:  self._check_stmt(stmt.initializer)
        if stmt.condition:    self._check_expr(stmt.condition)
        if stmt.increment:    self._check_expr(stmt.increment)
        self._check_stmt(stmt.body)
        self._end_scope()

    # ── Expr 방문 ─────────────────────────────────────────
    def _check_expr(self, expr: Expr) -> None:
        if isinstance(expr, VariableExpr):
            name = expr.name.origin
            if self._scopes and name in self._scopes[-1] and not self._scopes[-1][name]:
                raise CheckError(expr.name.line, "자신의 초기화식에서 지역변수를 읽을 수 없습니다.")
        elif isinstance(expr, AssignExpr):
            self._check_expr(expr.value)
        elif isinstance(expr, BinaryExpr):
            self._check_expr(expr.left)
            self._check_expr(expr.right)
        elif isinstance(expr, UnaryExpr):
            self._check_expr(expr.right)
        elif isinstance(expr, GroupingExpr):
            self._check_expr(expr.expression)
        elif isinstance(expr, LogicalExpr):
            self._check_expr(expr.left)
            self._check_expr(expr.right)

    def _begin_scope(self) -> None: self._scopes.append({})
    def _end_scope(self)   -> None: self._scopes.pop()
```

**Checker 체크리스트:**
- [ ] `VarDeclStmt` 방문 시 현재 스코프에 중복 여부 확인
- [ ] `BlockStmt` 진입/종료 시 스코프 append/pop
- [ ] 변수 초기화 식 방문 전 `False`(미완) 마킹, 이후 `True`(완료) 마킹
- [ ] `VariableExpr`에서 `False` 상태 변수 참조 시 오류

---

### 6-4. Executor — 조재현

**역할:** Checker를 통과한 AST를 DFS로 순회하며 실제 실행하고 결과를 출력한다.

**핵심 개념 — Environment (변수 저장소):**

```
Global 환경
    ├── Local 환경 1  (BlockStmt { } 진입 시 생성)
    │     └── Local 환경 1-1  (중첩 블록)
    └── Local 환경 2
```

- 블록 `{` 진입 → `Environment(parent=현재환경)` 생성
- 블록 `}` 종료 → 이전 환경으로 복귀
- 변수 조회 시: 현재 환경 → 부모 → 부모의 부모 → ... → Global

**실행 메서드 구조:**

```python
# executor.py
from ast_nodes import *
from environment import Environment
from tokens import TokenType

class LangRuntimeError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")

class Executor:
    def __init__(self, stmts: list[Stmt]):
        self._stmts = stmts
        self._global  = Environment()
        self._current = self._global

    def execute(self) -> None:
        for stmt in self._stmts:
            self._exec_stmt(stmt)

    # ── Stmt 실행 ─────────────────────────────────────────
    def _exec_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, PrintStmt):
            val = self._eval(stmt.expression)
            print(self._stringify(val))

        elif isinstance(stmt, VarDeclStmt):
            val = self._eval(stmt.initializer) if stmt.initializer else None
            self._current.define(stmt.name.origin, val)

        elif isinstance(stmt, ExpressionStmt):
            self._eval(stmt.expression)

        elif isinstance(stmt, BlockStmt):
            self._exec_block(stmt.statements, Environment(parent=self._current))

        elif isinstance(stmt, IfStmt):
            if self._is_truthy(self._eval(stmt.condition)):
                self._exec_stmt(stmt.then_branch)
            elif stmt.else_branch:
                self._exec_stmt(stmt.else_branch)

        elif isinstance(stmt, ForStmt):
            if stmt.initializer:
                self._exec_stmt(stmt.initializer)
            while stmt.condition is None or self._is_truthy(self._eval(stmt.condition)):
                self._exec_stmt(stmt.body)
                if stmt.increment:
                    self._eval(stmt.increment)

    def _exec_block(self, stmts: list[Stmt], env: Environment) -> None:
        prev = self._current
        try:
            self._current = env
            for stmt in stmts:
                self._exec_stmt(stmt)
        finally:
            self._current = prev   # 블록 종료 시 반드시 이전 환경 복귀

    # ── Expr 평가 ─────────────────────────────────────────
    def _eval(self, expr: Expr):
        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, VariableExpr):
            return self._current.get(expr.name.origin)

        if isinstance(expr, AssignExpr):
            val = self._eval(expr.value)
            self._current.assign(expr.name.origin, val)
            return val

        if isinstance(expr, GroupingExpr):
            return self._eval(expr.expression)

        if isinstance(expr, UnaryExpr):
            right = self._eval(expr.right)
            op = expr.operator.type
            if op == TokenType.MINUS:
                self._check_number(expr.operator, right)
                return -right
            if op == TokenType.BANG:
                return not self._is_truthy(right)

        if isinstance(expr, BinaryExpr):
            left  = self._eval(expr.left)
            right = self._eval(expr.right)
            op    = expr.operator.type
            line  = expr.operator.line

            if op == TokenType.PLUS:
                if isinstance(left, float) and isinstance(right, float):
                    return left + right
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                raise LangRuntimeError(line, "피연산자는 반드시 숫자 또는 문자열이어야 합니다.")
            if op == TokenType.MINUS:
                self._check_numbers(expr.operator, left, right); return left - right
            if op == TokenType.STAR:
                self._check_numbers(expr.operator, left, right); return left * right
            if op == TokenType.SLASH:
                self._check_numbers(expr.operator, left, right)
                if right == 0:
                    raise LangRuntimeError(line, "0으로 나눈 오류")
                return left / right
            if op == TokenType.GREATER:
                self._check_numbers(expr.operator, left, right); return left > right
            if op == TokenType.LESS:
                self._check_numbers(expr.operator, left, right); return left < right

        if isinstance(expr, LogicalExpr):
            left = self._eval(expr.left)
            if expr.operator.type == TokenType.OR:
                return left if self._is_truthy(left) else self._eval(expr.right)
            # AND
            return self._eval(expr.right) if self._is_truthy(left) else left

        raise LangRuntimeError(0, "알 수 없는 Expr 타입")

    # ── 헬퍼 ─────────────────────────────────────────────
    def _is_truthy(self, val) -> bool:
        if val is None:        return False
        if isinstance(val, bool): return val
        return True   # 숫자, 문자열은 모두 truthy

    def _check_number(self, op, val) -> None:
        if not isinstance(val, float):
            raise LangRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _check_numbers(self, op, left, right) -> None:
        if not (isinstance(left, float) and isinstance(right, float)):
            raise LangRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _stringify(self, val) -> str:
        if val is None:   return "nil"
        if isinstance(val, bool): return "true" if val else "false"
        if isinstance(val, float):
            s = str(val)
            return s[:-2] if s.endswith(".0") else s
        return str(val)
```

**Executor 체크리스트:**
- [ ] `PrintStmt` 실행 및 stdout 출력
- [ ] `VarDeclStmt` → `Environment.define()`
- [ ] `AssignExpr` → `Environment.assign()` (미선언 변수는 `LangRuntimeError`)
- [ ] `BlockStmt` → 새 `Environment` 생성 후 실행, `finally`로 복귀 보장
- [ ] `IfStmt` → condition 평가 후 분기
- [ ] `ForStmt` → init → condition 루프 → body → increment
- [ ] 타입 불일치 `LangRuntimeError` 처리
- [ ] 미정의 변수 참조 `LangRuntimeError` 처리
- [ ] 0으로 나누기 `LangRuntimeError` 처리

---

## 7. Token 타입 전체 목록

| TokenType | 예시 | 설명 |
|-----------|------|------|
| `LEFT_PAREN` | `(` | 그룹핑 / 조건식 시작 |
| `RIGHT_PAREN` | `)` | 그룹핑 / 조건식 끝 |
| `LEFT_BRACE` | `{` | 블록 시작 |
| `RIGHT_BRACE` | `}` | 블록 끝 |
| `SEMICOLON` | `;` | 문장 구분자 |
| `PLUS` | `+` | 덧셈 / 문자열 연결 |
| `MINUS` | `-` | 뺄셈 / 단항 음수 |
| `STAR` | `*` | 곱셈 |
| `SLASH` | `/` | 나눗셈 |
| `EQUAL` | `=` | 대입 |
| `EQUAL_EQUAL` | `==` | 동등 비교 |
| `BANG` | `!` | 논리 부정 |
| `BANG_EQUAL` | `!=` | 불일치 비교 |
| `GREATER` | `>` | 초과 비교 |
| `GREATER_EQUAL` | `>=` | 이상 비교 |
| `LESS` | `<` | 미만 비교 |
| `LESS_EQUAL` | `<=` | 이하 비교 |
| `IDENTIFIER` | `x`, `calcSum` | 식별자 (변수명, 함수명) |
| `STRING` | `"hello"` | 문자열 리터럴 |
| `NUMBER` | `7`, `3.14` | 숫자 리터럴 (`float`) |
| `VAR` | `var` | 변수 선언 키워드 |
| `IF` | `if` | 조건문 키워드 |
| `ELSE` | `else` | else 키워드 |
| `FOR` | `for` | 반복문 키워드 |
| `PRINT` | `print` | 출력 키워드 |
| `TRUE` | `true` | 불리언 true |
| `FALSE` | `false` | 불리언 false |
| `AND` | `and` | 논리 AND |
| `OR` | `or` | 논리 OR |
| `EOF` | (끝) | 토큰 스트림 종료 |

> `//` 줄 주석은 Tokenizer가 자동으로 무시한다.

---

## 8. Expr 노드 전체 목록

| Expr 타입 | 필드 | 예시 코드 |
|-----------|------|-----------|
| `LiteralExpr` | `value: float \| str \| bool \| None` | `3`, `"hi"`, `true` |
| `VariableExpr` | `name: Token` | `a` (변수 참조) |
| `AssignExpr` | `name: Token`, `value: Expr` | `a = 3` |
| `BinaryExpr` | `left: Expr`, `operator: Token`, `right: Expr` | `1 + 2`, `a > 0` |
| `UnaryExpr` | `operator: Token`, `right: Expr` | `-x`, `!isExist` |
| `GroupingExpr` | `expression: Expr` | `(1 + 2)` |
| `LogicalExpr` | `left: Expr`, `operator: Token`, `right: Expr` | `a and b` |

---

## 9. Stmt 노드 전체 목록

| Stmt 타입 | 필드 | 예시 코드 |
|-----------|------|-----------|
| `ExpressionStmt` | `expression: Expr` | `a + 1;` |
| `PrintStmt` | `expression: Expr` | `print a;` |
| `VarDeclStmt` | `name: Token`, `initializer: Expr \| None` | `var a = 3;` |
| `BlockStmt` | `statements: list[Stmt]` | `{ ... }` |
| `IfStmt` | `condition: Expr`, `then_branch: Stmt`, `else_branch: Stmt \| None` | `if (a > 0) { ... } else { ... }` |
| `ForStmt` | `initializer: Stmt \| None`, `condition: Expr \| None`, `increment: Expr \| None`, `body: Stmt` | `for (var i = 0; i < 3; i = i + 1) { ... }` |

---

## 10. 예시 스크립트 및 실행 흐름

### 예시 1: 변수 선언 및 산술
```
var a = 3 + 7;
print a;
```
**AST:**
```
VarDeclStmt [name: a]
└── BinaryExpr(+)
    ├── LiteralExpr(3)
    └── LiteralExpr(7)
PrintStmt
└── VariableExpr(a)
```
**실행 결과:** `10`

---

### 예시 2: 조건문
```
var x = 10;
if (x > 5) {
    print "big";
} else {
    print "small";
}
```
**실행 결과:** `big`

---

### 예시 3: 반복문
```
for (var i = 0; i < 3; i = i + 1) {
    print "#";
}
```
**실행 결과:**
```
#
#
#
```

---

### 예시 4: 중첩 스코프
```
var ga = 3;
{
    var a = 2;
    {
        var a = 7;
        {
            print a;    # 출력: 7  (가장 인접한 스코프에서 찾음)
            print ga;   # 출력: 3  (Global에서 찾음)
        }
        print a;        # 출력: 7
    }
}
```

---

## 11. 오류 처리 명세

### Tokenizer 오류 (`TokenizeError`)

| 상황 | 오류 메시지 형식 |
|------|----------------|
| 인식 불가 문자 | `[N번째줄] 인식할 수 없는 문자: '@'` |
| 닫히지 않은 문자열 | `[N번째줄] 문자열이 닫히지 않았습니다.` |

### Parser 오류 (`ParseError`)

| 상황 | 오류 메시지 형식 |
|------|----------------|
| 세미콜론 누락 | `[N번째줄] ';' 가 필요합니다.` |
| 우항 없음 | `[N번째줄] 표현식이 필요합니다.` |
| 닫는 괄호 누락 | `[N번째줄] ')' 가 필요합니다.` |

### Checker 오류 (`CheckError`)

| 상황 | 오류 메시지 형식 |
|------|----------------|
| 같은 블록 중복 선언 | `[N번째줄] 변수 'x'이(가) 이미 이 스코프에 선언되어 있습니다.` |
| 초기화 시 자기 참조 | `[N번째줄] 자신의 초기화식에서 지역변수를 읽을 수 없습니다.` |

### Executor 오류 (`LangRuntimeError`)

> Python 내장 `RuntimeError`와 이름 충돌을 피하기 위해 `LangRuntimeError`로 명명

| 상황 | 오류 메시지 형식 |
|------|----------------|
| 타입 불일치 | `[N번째줄] 피연산자는 반드시 숫자여야 합니다.` |
| 미정의 변수 참조 | `[N번째줄] 미정의된 변수 'x'` |
| 0으로 나누기 | `[N번째줄] 0으로 나눈 오류` |

---

## 12. 개발 일정 및 규칙

### 일정

| 일차 | 내용 |
|------|------|
| 1~2일차 | Custom Language 설계, CodeFab 핵심 구현, Prompt Shell 제작 |
| 3~4일차 | 기능 추가 (function, 정적 배열, 실행 전 최적화 등), 리팩토링 |
| 5일차 | 발표 준비 (오전: PPT 제작, 오후: 발표) |

### 권장 파일 구조

```
project/
├── tokens.py          # TokenType, Token, KEYWORDS  (Tokenizer 팀)
├── ast_nodes.py       # Expr / Stmt 노드 클래스      (Parser 팀)
├── tokenizer.py       # Tokenizer, TokenizeError     (김종화, 이채연)
├── parser.py          # Parser, ParseError           (박준용, 송지영)
├── checker.py         # Checker, CheckError          (권은재)
├── environment.py     # Environment                  (조재현)
├── executor.py        # Executor, LangRuntimeError   (조재현)
└── prompt_shell.py    # main() 진입점, REPL 루프      (전체 협의)
```

### 개발 규칙

1. **TDD 필수 (1~2일차):** 구현 전 테스트 먼저 작성 (`pytest` 사용 권장)
2. **Unit Test + 리팩토링 (3~4일차):** TDD 없이도 테스트 유지
3. **Claude Code 사용 허용:** 단, 생성된 코드를 이해 없이 넘기지 말 것
4. **리팩토링 전/후 Commit 필수:** 발표 자료에 캡처 포함 필요
5. **코드 컨벤션:** PEP 8 준수 (snake_case, 들여쓰기 4칸)
6. **타입 힌트 권장:** 함수 시그니처에 `-> None`, `-> list[Token]` 등 명시

### 테스트 기준 스크립트

**작업 디렉토리의 `테스트 스크립트.md` 파일을 기준으로 전부 통과해야 한다.**  
(문법은 Custom 언어에 맞게 변경 가능, 단 동작의 의미(semantics)는 동일하게 유지)

테스트는 크게 두 범주로 나뉜다:

| 범주 | 내용 |
|------|------|
| **1. 정상 동작 테스트** | 올바른 코드가 기대 출력값을 내는지 확인 |
| **2. 에러 검출 테스트** | 잘못된 코드가 반드시 오류 메시지를 출력하는지 확인 |

#### 정상 동작 테스트 항목

- **표현식 / 연산자 / 우선순위 / 진리값** — 산술, 비교, 문자열 연결, boolean 출력 포맷 (`5.0` → `5`)
- **변수, 할당, 블록 스코프, 변수 shadowing** — 재할당, 안쪽 블록에서 바깥 변수 수정, 중첩 스코프 탐색
- **제어 흐름** — `if/else` 분기, `else`는 가장 가까운 `if`에 결합, `for` 반복문

#### 에러 검출 테스트 항목

| 에러 종류 | 검출 시점 | 예시 |
|-----------|-----------|------|
| 세미콜론 누락 | Parser | `print 1 + 2` |
| 닫는 괄호 누락 | Parser | `print (1 + 2;` |
| 잘못된 할당 대상 | Parser | `a + b = 3;` |
| 표현식 자리에 잘못된 토큰 | Parser | `print * 5;` |
| 초기화식에서 자기 참조 | Checker | `{ var a = a; }` |
| 같은 스코프 중복 선언 | Checker | `{ var a = "hi"; var a = 3; }` |
| 미정의 변수 참조 | Executor | `print notDefined;` |
| `+` 연산 타입 혼용 | Executor | `print 1 + "HI";` |
| 단항 `-`에 비숫자 적용 | Executor | `print -"FabCoding";` |

> 전체 스크립트 원문은 `테스트 스크립트.md` 참고

### 발표 자료 포함 항목

- [ ] 팀 이름 및 Custom Language 소개
- [ ] 인터프리터 파이프라인 설명
- [ ] 리팩토링 전/후 코드 비교 캡처
- [ ] 코드 리뷰 활동 캡처
- [ ] 데모 실행 결과
