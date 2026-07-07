# CodeFab Interpreter

Python으로 미니 스크립트 언어에 대한 인터프리터를 구현하였습니다.
`Assembler → Checker → Executor` 파이프라인을 거쳐 소스 코드를 직접 해석하고 실행합니다.

## 특징

- 변수 선언/대입 (`var`)
- 산술 연산 (`+ - * /`), 문자열 연결 (`+`)
- 비교/동등 연산 (`> < >= <= == !=`)
- 논리 연산 (`and`, `or`, 단락 평가 지원)
- 제어문 (`if / else`, `for`)
- 블록 스코프 (`{ ... }`)와 변수 섀도잉
- `print` 문
- `//` 한줄 주석
- 정적 검사: 스코프 내 중복 선언 및 초기화식 자기 참조 탐지

## 아키텍처

소스 코드가 실행되기까지 다음 파이프라인을 거칩니다.

```
source(str)
   │
   ▼
Tokenizer   ── list[Token] 생성 (어휘 분석)
   │
   ▼
Parser      ── list[Stmt] (AST) 생성 (구문 분석)
   │
   ▼
Checker     ── AST 정적 검사 (중복 선언 / 자기 참조 탐지)
   │
   ▼
Executor    ── AST를 순회하며 실제로 실행
```

- `Assembler`: Tokenizer + Parser를 묶어 `source → AST` 변환만 담당
- `CodeFabInterpreter`: Assembler → Checker → Executor 전체 파이프라인을 감싸는 퍼사드. 인스턴스 내부에 전역 `Environment`를 보관해서 `run()`을 여러 번 호출해도(대화형 셸처럼) 이전에 선언한 변수를 계속 이어서 쓸 수 있다.

## 프로젝트 구조

```
interpreter/
├── tokens.py      # TokenType, Token 정의
├── tokenizer.py   # 소스 문자열 → list[Token]
├── ast_nodes.py   # Expr / Stmt AST 노드 정의
├── parser.py      # list[Token] → list[Stmt] (AST)
├── checker.py     # AST 정적 검사 (스코프/중복 선언 등)
├── executor.py     # AST 실행 (Environment 기반 스코프 체인)
├── assembler.py    # Tokenizer + Parser 파이프라인
└── codefab.py      # 전체 파이프라인 진입점 (CodeFabInterpreter)

prompt_shell.py      # 대화형 셸(REPL) CLI 진입점

tests/
├── test_tokenizer.py
├── test_parser.py
├── test_checker.py
├── test_assembler.py
└── test_executor.py
```

## 시작하기

### 요구 사항

- Python 3.10+ (`match` 문, `X | Y` 타입 힌트 사용)
- pytest 9.1.1


### 사용 예시

CodeFab은 두 가지 방식으로 실행할 수 있습니다: 코드에서 `CodeFabInterpreter`를 직접 호출하거나, 대화형 셸(REPL)로 한 줄씩 입력해서 실행합니다.

**1) 코드에서 직접 실행**

```python
from interpreter.codefab import CodeFabInterpreter

source = """
var a = 1;
var b = 2;
if (a < b) {
    print "a is less than b";
} else {
    print "a is not less than b";
}

for (var i = 0; i < 3; i = i + 1) {
    print i;
}

print (1 + 2) * 3;
print "Hello, " + "CodeFab!";
"""

CodeFabInterpreter().run(source)
```

출력:

```
a is less than b
0
1
2
9
Hello, CodeFab!
```

**2) 대화형 셸 (Prompt Shell)**

Python 인터프리터(`python` 명령)처럼 한 줄씩 입력해서 바로 실행해볼 수 있는 REPL도 제공합니다.

```bash
python prompt_shell.py
```

```
>> var a = 1;
>> print a + 1;
2
>> print a;
1
```

- 한 줄 입력할 때마다 `CodeFabInterpreter.run()`이 그 줄만 실행하지만, 같은 인터프리터 인스턴스를 계속 재사용하므로 이전 줄에서 선언한 변수를 다음 줄에서도 그대로 사용할 수 있습니다.
- `exit`, `exit()`, `quit`, `quit()` 입력 시 셸을 종료합니다.
- `Ctrl+C`: 현재 입력만 취소하고 새 프롬프트로 (파이썬 셸과 동일)
- `Ctrl+D`(Unix) / `Ctrl+Z` + `Enter`(Windows): 셸 종료
- Tokenize/Parse/Check/Runtime 에러가 나도 셸이 죽지 않고 에러 메시지만 출력한 뒤 다음 입력을 받습니다.

## 지원 토큰

`interpreter/tokens.py`의 `TokenType`에 정의된 토큰 종류입니다.

| 분류 | 토큰 | 설명 |
| --- | --- | --- |
| 구분자 | `(` `)` `{` `}` `;` `,` | 괄호, 중괄호, 세미콜론, 콤마 |
| 산술 연산자 | `+` `-` `*` `/` | 덧셈/뺄셈(문자열 `+`는 연결), 곱셈, 나눗셈 |
| 비교/대입 연산자 | `=` `==` `>` `<` `>=` `<=` `!` `!=` | 대입, 동등/부등, 대소 비교, 논리 부정 |
| 리터럴 | `IDENTIFIER` `STRING` `NUMBER` | 변수/함수명, `"hello"` 형태 문자열, `37`·`3.14` 형태 숫자(내부적으로 float) |
| 키워드 | `var` `if` `else` `for` `print` `true` `false` `and` `or` | 예약어 |
| 기타 | `EOF` | 토큰 스트림의 끝 |

`//`로 시작하는 한줄 주석은 토큰으로 만들어지지 않고 Tokenizer 단계에서 바로 무시됩니다.

## 언어 문법

```
program    → statement* EOF
statement  → varDecl | block | ifStmt | forStmt | printStmt | exprStmt
varDecl    → "var" IDENTIFIER "=" expression ";"
block      → "{" statement* "}"
ifStmt     → "if" "(" expression ")" statement ( "else" statement )?
forStmt    → "for" "(" (varDecl | exprStmt | ";") expression? ";" expression? ")" statement
printStmt  → "print" expression ";"
exprStmt   → expression ";"

expression → assignment
assignment → IDENTIFIER "=" assignment | logic_or
logic_or   → logic_and ( "or" logic_and )*
logic_and  → equality ( "and" equality )*
equality   → comparison ( ( "==" | "!=" ) comparison )*
comparison → term ( ( "<" | ">" | "<=" | ">=" ) term )*
term       → factor ( ( "+" | "-" ) factor )*
factor     → unary ( ( "*" | "/" ) unary )*
unary      → ( "!" | "-" ) unary | primary
primary    → NUMBER | STRING | "true" | "false" | IDENTIFIER | "(" expression ")"
```

## 테스트

각 모듈(Tokenizer/Parser/Checker/Executor/Assembler/Prompt Shell)은 `pytest` 기반 TDD로 개발되었습니다.
구현에 앞서 기대 동작에 대한 테스트를 먼저 작성하고, 테스트를 통과시키는 방향으로 구현을 진행했습니다.

테스트 수는 `pytest --collect-only`로 센 실제 실행 케이스 기준입니다(`@pytest.mark.parametrize`로 늘어난 케이스 포함).

| 클래스 / 파일 (`interpreter/`) | 테스트 파일 (`tests/`) | 테스트 수 |
| --- | --- | --- |
| `Token`, `TokenType` (`tokens.py`) / `Tokenizer`, `TokenizeError` (`tokenizer.py`) | `test_tokenizer.py` | 45 |
| `Expr` / `Stmt` 및 하위 AST 노드 (`ast_nodes.py`) / `Parser`, `ParseError` (`parser.py`) | `test_parser.py` | 46 |
| `Checker`, `CheckError` (`checker.py`) | `test_checker.py` | 9 |
| `Executor`, `Environment`, `LangRuntimeError` (`executor.py`) | `test_executor.py` | 68 |
| `Assembler` (`assembler.py`) | `test_assembler.py` | 28 |
| `CodeFabInterpreter` (`codefab.py`) / `run()` (`prompt_shell.py`) | `test_prompt_shell.py` | 46 |


## 기여

PR을 올릴 때는 `.github/pull_request_template.md` 양식을 따라주세요.
