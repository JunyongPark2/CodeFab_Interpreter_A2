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
- 실행 전 최적화: 정적 바인딩(변수 참조 O(1) 접근) + 상수 폴딩(리터럴 하위 트리 미리 계산)
- `import "파일경로" alias 별칭;` — 다른 CodeFab 소스 파일을 모듈처럼 불러오기

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
Checker     ── AST 정적 검사 + 실행 전 최적화 (정적 바인딩 계산 / 상수 폴딩)
   │
   ▼
Executor    ── AST를 순회하며 실제로 실행 (정적 바인딩 결과로 변수 O(1) 접근)
```

- `Assembler`: Tokenizer + Parser를 묶어 `source → AST` 변환만 담당
- `CodeFabInterpreter`: Assembler → Checker → Executor 전체 파이프라인을 감싸는 퍼사드. 인스턴스 내부에 전역 `Environment`를 보관해서 `run()`을 여러 번 호출해도(대화형 셸처럼) 이전에 선언한 변수를 계속 이어서 쓸 수 있다.

### 실행 전 최적화 (정적 바인딩 / 상수 폴딩)

별도의 `Optimizer` 단계를 추가하는 대신, `Checker`의 역할을 확장해서 검사와 동시에
두 가지 최적화를 수행한다. 파이프라인 구조(`Assembler → Checker → Executor`)는 그대로다.

- **정적 바인딩**: `var`/블록(`{ }`)/`for` 스코프 안에서 변수를 참조하면, `Checker`가
  검사 시점에 "몇 단계 바깥 스코프에 있는지"(distance)를 미리 계산해둔다. `Executor`는
  이 정보로 `Environment.get_at`/`assign_at`을 호출해 스코프 체인을 매번 동적으로
  거슬러 올라가지 않고 O(1)로 바로 접근한다. **최상위(전역) 변수는 대상에서 제외**되며
  기존처럼 `Environment.get`/`assign`으로 동적 조회한다. `Func`/`Class` 본문도
  동일한 스코프 스택 메커니즘을 그대로 재사용하므로 별도 확장 없이 자동으로 적용되며,
  클래스 메서드 안의 `This` 참조도 `Super`와 동일하게 이 방식으로 O(1) 접근한다.
- **상수 폴딩**: `1 + 2 * 3`처럼 리터럴로만 이루어진 하위 표현식은 `Checker`가 검사
  중에 미리 계산해서 하나의 리터럴로 치환해둔다. 단, **0으로 나누기나 타입이 맞지 않는
  연산처럼 실행 시 에러가 나야 하는 식은 절대 접지 않는다** — 그런 식은 그대로 두어
  `Executor`가 평소와 동일한 시점에 동일한 런타임 에러를 내도록 보장한다.

이 최적화는 언어 문법이나 사용자가 작성하는 코드에는 영향을 주지 않는다 — 같은 소스
코드를 실행했을 때 관찰 가능한 동작(출력 결과, 에러 발생 여부/메시지)은 최적화 전후로
동일하며, 오직 실행 속도만 개선된다.

### import — 다른 CodeFab 파일 불러오기

```
import "sum.txt" alias sum;
```

- **문법**: `import STRING alias IDENTIFIER;` — 경로는 반드시 문자열 리터럴이어야 한다.
- **어디서든 작성 가능하지만 `for` 반복문 내부(중첩된 블록/if 포함)에서는 금지**된다.
  파싱 단계에서 곧바로 `ParseError`로 걸러진다.
- import되는 파일의 최상위에는 **선언(다른 파일 `import`, 함수 선언 `Func`, 전역 변수
  선언 `var`)만 허용**된다. 그 외의 문장(예: `print`, `if`)이 있으면 파일을 실행하기
  전에 `ModuleImportError`가 발생한다 — 그런 코드가 조용히 무시되면 실행 순서가
  파일마다 달라져 디버깅이 어려워지기 때문에, 명확한 오류로 처리하기로 했다.
- import된 선언은 **import 문이 실행된 스코프에서만 유효**하다. 같은 스코프에서 같은
  파일을 다시 import하거나, 이미 import된 파일을 하위(중첩) 스코프에서 다시
  import하면 `CheckError`가 발생한다. 다만 스코프가 끝나면 그 기록도 사라지므로,
  서로 다른 형제 블록에서 각각 같은 파일을 import하는 것은 허용된다.
- 순환 import(a가 b를, b가 다시 a를 import)는 `ModuleImportError`로 즉시 차단된다.
- 대상 파일이 존재하지 않아도 `ModuleImportError`가 발생한다.
- **현재 알려진 제약**: `sum.add(1, 2)`처럼 `.`으로 모듈 멤버에 접근하는 문법은 아직
  지원되지 않는다. 이 문법은 Class 기능의 `GetExpr`(`.` 접근)/`CallExpr` 파싱·실행
  로직을 그대로 재사용하도록 설계되어 있어서, Class 기능이 merge된 뒤에 마저 연결할
  예정이다. 그 전까지 import 자체(파일 로드, alias 변수에 모듈 객체 저장)는 정상
  동작하며, `LangModule.fields`를 통해 내부적으로는 모듈의 함수/변수를 담고 있다.

## 프로젝트 구조

```
interpreter/
├── tokens.py       # TokenType, Token 정의
├── tokenizer.py    # 소스 문자열 → list[Token]
├── ast_nodes.py    # Expr / Stmt AST 노드 정의
├── parser.py       # list[Token] → list[Stmt] (AST)
├── checker.py      # AST 정적 검사 + 실행 전 최적화 (정적 바인딩 / 상수 폴딩)
├── environment.py  # Environment (스코프 체인, get_at/assign_at으로 O(1) 접근 지원)
├── errors.py       # TokenizeError / ParseError / CheckError / LangRuntimeError / ModuleImportError
├── executor.py     # AST 실행 (정적 바인딩 결과를 받아 변수 접근에 활용)
├── assembler.py    # Tokenizer + Parser 파이프라인
├── loader.py       # import 대상 파일 로드 + 순환 import 탐지 (Assembler 재사용)
└── codefab.py      # 전체 파이프라인 진입점 (CodeFabInterpreter)

prompt_shell.py      # 대화형 셸(REPL) CLI 진입점

tests/
├── test_tokenizer.py
├── test_parser.py
├── test_checker.py
├── test_assembler.py
├── test_executor.py
├── test_executor_import.py  # import 실행 end-to-end 테스트
├── test_environment.py
├── test_loader.py
├── test_optimization.py   # 정적 바인딩/상수 폴딩 Test Double(스파이) 검증
├── test_codefab.py
└── test_prompt_shell.py
```

## 시작하기

### 요구 사항

- Python 3.10+ (`match` 문, `X | Y` 타입 힌트 사용)
- pytest 9.1.0


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

문장이 아직 끝나지 않았으면(예: `if`/`for`의 본문이나 블록이 안 닫힌 경우) Python 셸처럼 `...` 프롬프트로 다음 줄을 계속 이어받다가, 문장이 완성되는 순간 실행합니다.

```
>> if (true)
... {
...   print "bbq";
... }
bbq
```

- 한 줄 입력할 때마다 `CodeFabInterpreter.run()`이 그 문장만 실행하지만, 같은 인터프리터 인스턴스를 계속 재사용하므로 이전 줄에서 선언한 변수를 다음 줄에서도 그대로 사용할 수 있습니다.
- `exit`, `exit()`, `quit`, `quit()` 입력 시 셸을 종료합니다.
- `Ctrl+C`: 현재 입력(이어받던 블록 포함)만 취소하고 새 프롬프트로 (파이썬 셸과 동일)
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
| 키워드 | `var` `if` `else` `for` `print` `true` `false` `and` `or` `import` `alias` | 예약어 |
| 기타 | `EOF` | 토큰 스트림의 끝 |

`//`로 시작하는 한줄 주석은 토큰으로 만들어지지 않고 Tokenizer 단계에서 바로 무시됩니다.

## 언어 문법

```
program    → statement* EOF
statement  → varDecl | block | ifStmt | forStmt | printStmt | importStmt | exprStmt
varDecl    → "var" IDENTIFIER "=" expression ";"
block      → "{" statement* "}"
ifStmt     → "if" "(" expression ")" statement ( "else" statement )?
forStmt    → "for" "(" (varDecl | exprStmt | ";") expression? ";" expression? ")" statement
printStmt  → "print" expression ";"
importStmt → "import" STRING "alias" IDENTIFIER ";"   # for 본문 내부에서는 사용 불가
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
| `Token`, `TokenType` (`tokens.py`) / `Tokenizer` (`tokenizer.py`) | `test_tokenizer.py` | 58 |
| `Expr` / `Stmt` 및 하위 AST 노드 (`ast_nodes.py`) / `Parser` (`parser.py`) | `test_parser.py` | 61 |
| `Checker` (`checker.py`) — 정적 검사 + 상수 폴딩/정적 바인딩 계산 + import 검사 | `test_checker.py` | 55 |
| `Executor` (`executor.py`) | `test_executor.py` | 78 |
| 함수(Function) 실행 (`executor.py`) | `test_executor_function.py` | 34 |
| import 실행 end-to-end (`executor.py`, `loader.py`, `codefab.py`) | `test_executor_import.py` | 12 |
| `Environment` (`environment.py`) — `get_at`/`assign_at` 포함 | `test_environment.py` | 9 |
| `Loader` (`loader.py`) — 파일 로드 / 순환 import 탐지 | `test_loader.py` | 8 |
| 실행 전 최적화 Test Double 검증 (monkeypatch 스파이) | `test_optimization.py` | 3 |
| `Assembler` (`assembler.py`) | `test_assembler.py` | 45 |
| `CodeFabInterpreter` (`codefab.py`) | `test_codefab.py` | 34 |
| `run()`, 대화형 입력 처리 (`prompt_shell.py`) | `test_prompt_shell.py` | 75 |

`TokenizeError` / `ParseError` / `CheckError` / `LangRuntimeError`는 모두 `errors.py`에 정의되어 있으며, 위 표의 각 테스트 파일에서 함께 검증됩니다.


## 기여

PR을 올릴 때는 `.github/pull_request_template.md` 양식을 따라주세요.
