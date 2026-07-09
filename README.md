# CodeFab Interpreter

Python으로 구현한 미니 스크립트 언어 인터프리터입니다. CodeFab 소스 코드를
`Assembler(Tokenizer -> Parser) -> Checker -> Executor` 파이프라인으로 처리합니다.

이 프로젝트는 변수, 제어문, 함수, 클래스, 상속, 정적 배열, 파일 import를 지원하는
인터프리터입니다. 구현은 `interpreter/` 아래에 모듈별로 분리되어 있고,
672개의 pytest 테스트로 현재 동작을 검증합니다.

## 주요 기능

- 변수 선언/대입: `var x = 1;`, `x = x + 1;`
- 기본 타입: `Number`, `String`, `Boolean`, `null`
- 산술/비교/동등 연산: `+ - * / %`, `< > <= >=`, `== !=`
- 논리 연산: `and`, `or`, `!` 및 단락 평가
- 제어문: `if / else`, C 스타일 `for`
- 블록 스코프와 변수 섀도잉
- `print` 문과 `//` 한 줄 주석
- 함수: `Func`, 매개변수, 재귀, 클로저, `return`
- 클래스: `Class`, 동적 필드, 메서드, `This`, 생성자 `init`
- 단일 상속: `Class Child : Parent`, `Super`, `instanceof`
- 정적 배열: `Array(n)`, `arr[i]` 읽기/쓰기
- import: `import "path" alias name;` 및 `name.member` 접근
- 실행 전 검사/최적화: 중복 선언 검사, 자기 참조 검사, 정적 바인딩, 상수 폴딩
- Factory Shell 디버그 모드: `step`, `next`, `break`, `watch`, `inspect`

## 추가 기능 구현 Checklist

`3일차_CodeFab Interpreter.pdf`의 추가 기능 요청을 기준으로 정리한 구현 현황입니다.

- [x] function 관련 요구사항
- [x] class 관련 요구사항
- [x] 정적 배열 구현
- [x] 실행전 최적화
- [x] import 관련 요구사항
- [x] 공장 제어 쉘 제작

## 프로젝트 구조

```text
interpreter/
├── tokens.py       # TokenType, Token 정의
├── tokenizer.py    # Assembler 내부에서 source(str) -> list[Token] 변환
├── ast_nodes.py    # Expr / Stmt AST 노드
├── parser.py       # Assembler 내부에서 list[Token] -> list[Stmt] 변환
├── checker.py      # 정적 검사 + 정적 바인딩 + 상수 폴딩
├── environment.py  # 스코프 체인, get_at/assign_at
├── errors.py       # Tokenize/Parse/Check/Runtime/Import 에러
├── runtime.py      # 함수/클래스/인스턴스/모듈 런타임 값
├── executor.py     # AST 실행기
├── debugger.py     # 문장 단위 디버그 컨트롤러
├── assembler.py    # Tokenizer와 Parser를 감싸 source -> AST 변환
├── loader.py       # import 대상 파일 로드와 순환 import 탐지
└── codefab.py      # CodeFabInterpreter 퍼사드

prompt_shell.py     # 대화형 REPL
factory_shell.py    # REPL / 파일 실행 / 디버그 모드 CLI
tests/              # pytest 테스트
```

## 설치

런타임 자체는 외부 패키지에 의존하지 않습니다. 테스트까지 실행하려면 `pytest`와
`pytest-cov`가 필요합니다. `pyproject.toml`에 coverage 옵션이 들어 있으므로,
`pytest-cov` 없이 `python -m pytest`를 실행하면 옵션 인식 오류가 납니다.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
pip install -e .
```

editable install 후에는 `factory` 명령어가 등록됩니다.

```bash
factory
factory run <파일경로>
factory debug <파일경로>
```

설치를 해제하려면 다음 명령을 사용합니다.

```bash
pip uninstall codefab-interpreter
```

## 사용 방법

설치 후 `factory` 명령어로 REPL, 파일 실행, 디버그 모드를 사용할 수 있습니다.

```bash
factory                          # REPL 모드
factory run <파일경로>             # 파일 실행 모드
factory debug <파일경로>           # 디버그 모드
```

설치하지 않고 저장소에서 바로 실행할 수도 있습니다.

```bash
python factory_shell.py                          # REPL 모드
python factory_shell.py run <파일경로>             # 파일 실행 모드
python factory_shell.py debug <파일경로>           # 디버그 모드
```

### REPL 모드

인자 없이 `factory`를 실행하면 대화형 셸이 시작됩니다.

```bash
factory
```

```text
>> var a = 1;
>> print a + 1;
2
>> print a;
1
```

문장이 아직 끝나지 않았으면 `...` 프롬프트로 이어서 입력을 받습니다.

```text
>> if (true) {
...   print "ok";
... }
...
ok
```

REPL 종료 명령:

- `exit`
- `exit()`
- `quit`
- `quit()`
- Unix/macOS: `Ctrl+D`
- Windows: `Ctrl+Z` 후 `Enter`

`Ctrl+C`는 현재 입력 중인 버퍼만 취소하고 새 프롬프트로 돌아갑니다.

### 파일 실행 모드

```bash
factory run <파일경로>
```

파일이 없거나 실행 중 오류가 발생하면 메시지를 출력하고 종료 코드 `1`로 종료합니다.

### 디버그 모드

```bash
factory debug <파일경로>
```

디버그 모드는 AST의 `Stmt` 단위로 멈춰가며 실행합니다. 첫 번째 문장에서 자동으로
정지하며, import된 모듈 내부 문장도 같은 방식으로 stepping 대상이 됩니다.

| 명령어 | 설명 |
| --- | --- |
| `step` | 현재 문장을 실행하고 다음 문장에서 정지합니다. 블록/함수/import 내부로 들어갑니다. |
| `next` | 현재 문장을 실행하고 같은 깊이의 다음 문장에서 정지합니다. 블록 내부로 들어가지 않습니다. |
| `continue` | 다음 breakpoint 또는 프로그램 종료까지 실행합니다. |
| `break <줄번호>` | 해당 줄에 breakpoint를 설정합니다. |
| `breakpoints` | 설정된 breakpoint 목록을 출력합니다. |
| `remove <줄번호>` | 해당 줄의 breakpoint를 해제합니다. |
| `watch <변수명>` | 정지할 때마다 변수 값을 출력하도록 등록합니다. |
| `unwatch <변수명>` | watch 목록에서 제거합니다. |
| `watches` | 현재 watch 목록과 값을 출력합니다. |
| `inspect` | 현재 스코프에서 보이는 변수와 타입을 출력합니다. |
| `exit`, `exit()`, `quit`, `quit()` | 디버그 세션을 종료합니다. |

예시:

```bash
factory debug <파일경로>
```

```text
[DEBUG] 소스코드 로딩: program.txt
[DEBUG] program.txt:1번째 줄에서 정지
    → var total = 0;
> step
```

## 언어 예시

### 함수

```codefab
Func factorial(n) {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

print factorial(5);   // 120
```

함수는 선언 시점의 환경을 캡처하므로 클로저처럼 동작합니다. `return;` 또는 함수 끝까지
도달한 경우 반환값은 `null`입니다.

### 클래스와 상속

```codefab
Class Robot {
    init(name, speed) {
        This.name = name;
        This.speed = speed;
    }

    move(dist) {
        This.speed = This.speed + dist;
    }
}

Class SpeedRobot : Robot {
    move(dist) {
        Super.move(dist);
        print "Speeeed!";
    }
}

var r = SpeedRobot("Arm", 10);
r.move(5);
print r.speed;
print r instanceof Robot;
```

출력:

```text
Speeeed!
15
true
```

클래스 메서드는 `Func` 키워드 없이 `name(...) { ... }` 형태로 작성합니다.
`This`, `Super`, `Class`는 대문자로 시작하는 키워드이며, 소문자 `this`, `super`,
`class`는 일반 식별자입니다.

### 배열

```codefab
var arr = Array(3);
arr[0] = 10;
arr[1] = 20;
print arr[0] + arr[1];   // 30
print arr;               // [10, 20, null]
```

배열 크기와 인덱스는 0 이상의 정수여야 합니다. 범위를 벗어난 접근은 런타임 에러입니다.

### import

`mathlib.txt`:

```codefab
Func add(a, b) {
    return a + b;
}

var VERSION = 1;
```

실행 파일:

```codefab
import "mathlib.txt" alias math;

print math.add(1, 2);
print math.VERSION;
```

출력:

```text
3
1
```

import된 파일은 독립된 모듈 네임스페이스에서 실행되고, alias를 통해 읽기 전용으로 접근합니다.
`math.x = 1;`처럼 모듈 멤버에 값을 대입하는 것은 지원하지 않습니다.

## 언어 문법 요약

```text
program     -> statement* EOF

statement   -> varDecl | funcDecl | classDecl | block | ifStmt | forStmt
             | returnStmt | printStmt | importStmt | exprStmt

varDecl     -> "var" IDENTIFIER ( "=" expression )? ";"
funcDecl    -> "Func" IDENTIFIER "(" parameters? ")" block
classDecl   -> "Class" IDENTIFIER ( ":" IDENTIFIER )? "{" method* "}"
method      -> IDENTIFIER "(" parameters? ")" block
parameters  -> IDENTIFIER ( "," IDENTIFIER )*

block       -> "{" statement* "}"
ifStmt      -> "if" "(" expression ")" statement ( "else" statement )?
forStmt     -> "for" "(" ( varDecl | exprStmt | ";" )
               expression? ";" expression? ")" statement
returnStmt  -> "return" expression? ";"
printStmt   -> "print" expression ";"
importStmt  -> "import" STRING "alias" IDENTIFIER ";"
exprStmt    -> expression ";"

expression  -> assignment
assignment  -> lvalue "=" assignment
             | logic_or
lvalue      -> IDENTIFIER
             | call "." IDENTIFIER
             | primary "[" expression "]" ( "[" expression "]" )*
logic_or    -> logic_and ( "or" logic_and )*
logic_and   -> equality ( "and" equality )*
equality    -> instanceof ( ( "==" | "!=" ) instanceof )*
instanceof  -> comparison ( "instanceof" IDENTIFIER )?
comparison  -> term ( ( "<" | ">" | "<=" | ">=" ) term )*
term        -> factor ( ( "+" | "-" ) factor )*
factor      -> unary ( ( "*" | "/" | "%" ) unary )*
unary       -> ( "!" | "-" ) unary | call
call        -> index ( "(" arguments? ")" | "." IDENTIFIER )*
index       -> primary ( "[" expression "]" )*
arguments   -> expression ( "," expression )*

primary     -> NUMBER | STRING | "true" | "false"
             | "This" | "Super" "." IDENTIFIER
             | IDENTIFIER | "Array" "(" expression ")"
             | "(" expression ")"
```

## 토큰과 리터럴

| 분류 | 토큰/형태 | 비고 |
| --- | --- | --- |
| 구분자 | `(` `)` `{` `}` `[` `]` `;` `,` `.` `:` | 블록, 호출, 인덱스, 속성 접근, 상속 등에 사용 |
| 산술 | `+` `-` `*` `/` `%` | `+`는 숫자 덧셈 또는 문자열 연결 |
| 비교/대입 | `=` `==` `>` `<` `>=` `<=` `!` `!=` | `!`는 논리 부정 |
| 리터럴 | `NUMBER`, `STRING`, `true`, `false` | 숫자는 내부적으로 `float` |
| 기본 키워드 | `var`, `if`, `else`, `for`, `print`, `and`, `or` | 소문자 |
| 함수/클래스 | `Func`, `return`, `Class`, `This`, `Super`, `instanceof` | 일부 키워드는 대소문자 구분 |
| 배열/import | `Array`, `import`, `alias` | `Array`는 대문자 시작 |

문자열은 큰따옴표와 작은따옴표를 모두 지원합니다.

```codefab
print "hello";
print 'hello';
```

현재 토크나이저는 escape sequence를 따로 해석하지 않습니다. 같은 종류의 따옴표가 다시
나올 때 문자열이 종료됩니다.

## 아키텍처

```text
source(str)
   |
   v
Assembler  -> Tokenizer -> Parser -> list[Stmt] AST
   |
   v
Checker    -> 정적 검사 + locals_map 계산 + 상수 폴딩
   |
   v
Executor   -> AST 실행
```

- `Assembler`는 `Tokenizer`와 `Parser`를 감싸는 조립 계층입니다. 외부 파이프라인에서는
  `Assembler`가 하나의 단계로 보이며, 내부에서 토큰화와 파싱을 순서대로 수행해
  `source -> AST` 변환만 담당합니다.
- `Checker`는 중복 선언, 초기화식 자기 참조, `return` 위치, `This`/`Super` 사용 위치,
  import 중복 등을 검사합니다.
- `Checker`는 실행 전 최적화를 위해 AST 일부를 바꿀 수 있습니다. 리터럴만으로 이루어진
  하위 표현식은 `LiteralExpr`로 접고, 지역 변수 참조는 몇 단계 바깥 스코프인지
  `locals_map`에 기록합니다.
- `Executor`는 `locals_map`이 있는 지역 변수는 `Environment.get_at()`/`assign_at()`으로
  바로 접근하고, 전역 변수는 기존 동적 조회를 사용합니다.
- `CodeFabInterpreter`는 `Assembler -> Checker -> Executor` 전체 파이프라인을 감싸며,
  REPL을 위해 전역 환경과 최상위 import 기록을 인스턴스 내부에 유지합니다.
- AST 노드는 `accept()` 기반 더블 디스패치를 사용합니다. 새 노드 타입에 대응하는
  visitor 메서드가 없으면 즉시 `NotImplementedError`를 발생시켜 누락을 드러냅니다.
- 디버거는 `Executor`의 `on_stmt` 훅으로 연결되어 실행 로직과 디버그 제어를 분리합니다.

## import 규칙과 특이사항

- 문법은 `import STRING alias IDENTIFIER;`입니다.
- import 경로는 현재 프로세스의 작업 디렉터리 기준으로 해석합니다. import하는 파일의
  위치를 기준으로 상대 경로를 다시 계산하지 않습니다.
- `for` 본문 내부에서는 import를 사용할 수 없습니다. 중첩 블록이나 `if` 안이어도
  `for` 본문 안이면 `ParseError`입니다.
- import 대상 파일의 최상위에는 `import`, `Func`, `var` 선언만 올 수 있습니다.
  `print`, `if`, 표현식 문장 등은 `ModuleImportError`입니다.
- 모듈은 독립된 환경에서 실행됩니다. import하는 쪽의 지역/전역 변수를 직접 볼 수 없습니다.
- import된 선언은 alias 아래의 읽기 전용 네임스페이스로 노출됩니다.
- 같은 스코프나 상위 스코프에서 이미 import한 파일을 다시 import하면 `CheckError`입니다.
- 형제 블록에서는 같은 파일을 각각 import할 수 있습니다. 블록 스코프가 끝나면 그 블록의
  import 기록도 사라집니다.
- `CodeFabInterpreter` 하나를 여러 번 `run()`하는 경우 최상위 import 기록은 유지됩니다.
  서로 다른 `CodeFabInterpreter` 인스턴스끼리는 import 기록을 공유하지 않습니다.
- 순환 import는 `ModuleImportError`로 차단됩니다.

## 기타 특이사항

- 모든 문장은 세미콜론으로 끝나야 합니다. 블록/클래스 선언 자체에는 세미콜론을 붙이지
  않습니다.
- 숫자는 내부적으로 `float`입니다. 출력할 때 `5.0`처럼 정수로 표현 가능한 값은 `5`로
  표시합니다.
- 초기화하지 않은 변수, 값 없는 `return`, 반환 없이 끝난 함수의 값은 `null`입니다.
- truthy/falsy 규칙은 단순합니다. `false`와 `null`만 falsy이고, `0`, 빈 문자열, 빈 배열은
  truthy입니다.
- 같은 스코프의 중복 선언은 `CheckError`입니다. 하위 블록에서 같은 이름을 다시 선언하는
  섀도잉은 허용됩니다.
- `for`의 initializer로 선언한 변수는 루프 스코프 안에서만 유효합니다.
- `return`은 함수 안에서만 사용할 수 있습니다.
- `init` 메서드 안에서는 값 있는 `return`뿐 아니라 `return;`도 사용할 수 없습니다.
  생성자는 항상 인스턴스를 반환합니다.
- 클래스 필드는 선언 없이 동적으로 저장됩니다. 존재하지 않는 필드를 읽으면 런타임 에러입니다.
- `This`와 `Super`는 클래스 메서드 안에서만 사용할 수 있습니다. `Super`는 부모 클래스가
  있는 클래스에서만 사용할 수 있습니다.
- `break`, `continue`, 배열 리터럴, 배열 크기 변경 API, 모듈 멤버 대입은 현재 지원하지
  않습니다.
- 상수 폴딩은 런타임 에러 발생 시점을 바꾸지 않기 위해, 0으로 나누기나 타입 오류가 날 수
  있는 표현식은 접지 않습니다.
- 정적 바인딩은 전역 변수를 제외한 지역 변수에 적용됩니다. `get_at(distance)`는
  스코프별 이름 탐색을 건너뛰지만, `distance`만큼 parent를 따라 올라가는 포인터 이동은
  여전히 수행합니다.

## 에러 종류

| 에러 | 발생 단계 | 예 |
| --- | --- | --- |
| `TokenizeError` | 토큰화 | 알 수 없는 문자, 닫히지 않은 문자열 |
| `ParseError` | 파싱 | 세미콜론 누락, 잘못된 대입 대상, `for` 내부 import |
| `CheckError` | 정적 검사 | 같은 스코프 중복 선언, 초기화식 자기 참조, 함수 밖 `return` |
| `CodeFabRuntimeError` | 실행 | 미정의 변수, 0 나누기, 타입 오류, 배열 범위 초과 |
| `ModuleImportError` | import | 파일 없음, 순환 import, import 대상 파일의 허용되지 않는 최상위 문장 |

모든 에러 메시지는 `[N번째줄] ...` 형태로 줄 번호를 포함합니다.

## 테스트

전체 테스트 실행:

```bash
python -m pytest
```

coverage 없이 빠르게 실행:

```bash
python -m pytest --no-cov
```

테스트 수 집계:

```bash
python -m pytest --collect-only -q --no-cov
```

현재 가상환경에서 수집되는 테스트는 총 672개입니다.

| 테스트 파일 | 테스트 수 | 주요 검증 대상 |
| --- | ---: | --- |
| `tests/test_tokenizer.py` | 61 | 토큰화, 키워드, 문자열/숫자/주석 |
| `tests/test_parser.py` | 73 | 문법, 우선순위, import/class/array 파싱 |
| `tests/test_checker.py` | 80 | 정적 검사, 상수 폴딩, 정적 바인딩, class/import 검사 |
| `tests/test_executor.py` | 97 | 기본 실행, 제어문, 배열, 클래스/상속 실행 |
| `tests/test_executor_function.py` | 34 | 함수, 재귀, 클로저, return |
| `tests/test_executor_import.py` | 21 | import end-to-end, 모듈 멤버 접근, 순환/중복 import |
| `tests/test_environment.py` | 9 | 스코프 체인, `get_at`, `assign_at` |
| `tests/test_loader.py` | 8 | 파일 로드, 선언-only 검사, 순환 import context |
| `tests/test_optimization.py` | 5 | 정적 바인딩/상수 폴딩이 실제 실행 경로에 반영되는지 |
| `tests/test_assembler.py` | 55 | Assembler가 Tokenizer와 Parser를 감싸는 조립 흐름 |
| `tests/test_codefab.py` | 68 | `CodeFabInterpreter` end-to-end |
| `tests/test_debugger.py` | 52 | step/next/break/watch/inspect |
| `tests/test_factory_shell.py` | 27 | CLI 모드 분기, 파일/디버그 모드 오류 처리 |
| `tests/test_prompt_shell.py` | 77 | REPL 입력 누적, 오류 복구, 상태 유지 |
| `tests/test_visitor.py` | 5 | AST visitor dispatch 누락 방지 |

`python -m pytest`를 실행하면 `pyproject.toml`의 설정에 따라 터미널 coverage와
`htmlcov/` HTML 리포트가 함께 생성됩니다.

## 기여

PR을 올릴 때는 `.github/pull_request_template.md` 양식을 따라주세요.
