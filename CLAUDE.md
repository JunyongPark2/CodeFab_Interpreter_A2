# CodeFab Interpreter — Checker 담당자 작업 가이드

> 이 문서는 세션이 바뀌어도 항상 참고해야 하는 고정 컨텍스트다.
> 전체 프로젝트 스펙은 `CodeFab_Interpreter_Guide.md`, 최종 합격 기준은 `테스트 스크립트.md`.

## 담당자 정보
- 이름: 권은재
- 담당 모듈: **Checker Unit** (`checker.py`)
- 브랜치: `feature/checker`
- 팀 구성: Tokenizer(김종화, 이채연) / Parser(박준용, 송지영) / Checker(권은재, 본인) / Executor(조재현)

## Checker의 역할 (가이드 4-3, 6-3장)
```
Input  : list[Stmt]   # Parser가 생성한 AST
Output : None          # 오류 없으면 정상 반환, AST 수정 금지
Error  : CheckError
           - 같은 블록 내 변수 중복 선언
           - 변수 초기화식에서 자기 자신 참조
```
DFS로 AST를 순회하며 스코프 스택(`list[dict[str, bool]]`)으로 검사한다.
- `VarDeclStmt` 진입 시: 현재 스코프에 이미 있으면 중복선언 에러, 없으면 `False`(초기화 미완)로 등록
- initializer 평가 후 `True`(초기화 완료)로 갱신
- `VariableExpr` 방문 시 현재 스코프에서 `False` 상태인 이름을 읽으면 자기참조 에러
- `BlockStmt`/`ForStmt` 진입/종료 시 스코프 push/pop

## 내 판단: Checker 구현자가 책임져야 할 테스트 범위
`테스트 스크립트.md`의 "2) Checker Unit에서 검출하는 에러" 두 케이스가 직접 책임:
1. `{ var a = a; }` → 자기참조 에러
2. `{ var a = "hi"; var a = 3; }` → 중복선언 에러

**추가로**, "1. 정상동작 테스트"의 변수/블록스코프/shadowing/중첩스코프 케이스들은
Checker를 반드시 **에러 없이 통과**해야 한다 (Checker가 오탐하면 정상 프로그램이 막힘).
따라서 `test_checker.py`에는 에러 케이스뿐 아니라 정상 케이스(재할당, shadowing,
바깥 변수 수정, 중첩 스코프 참조, if/for 내부 var 선언)의 "예외 없이 통과" 검증도 포함한다.
Parser/Executor 전용 에러(세미콜론 누락, 미정의 변수 참조 등)는 내 책임이 아니다.

## 개발 방식: TDD (RED → GREEN → REFACTOR)
1. **RED**: `test_checker.py`에 실패하는 테스트 먼저 작성 (Checker 미구현 상태로 실행 → 전부 실패 확인)
2. **GREEN**: 가이드 스켈레톤 기반으로 `checker.py` 최소 구현 → 테스트 전부 통과
3. **REFACTOR**: 통과 유지하며 코드 정리 (타입힌트, 메서드 분리, 중복 제거)

## Assembler Unit 관련 처리
Tokenizer/Parser 팀 코드가 아직 다른 브랜치에도 없으므로, 가이드 5장 스펙과
100% 동일하게 `tokens.py`, `ast_nodes.py` 스텁을 직접 작성해 Checker를 개발/테스트한다.
실제 Assembler 코드가 합류해도 인터페이스가 동일하므로 교체 시 충돌 없음.

## 단계별 로드맵 (커밋 / 캡처 / PR 타이밍)

| 단계 | 내용 | 커밋 | 캡처(발표자료용) |
|------|------|------|------|
| 0 | CLAUDE.md 작성 (완료) | - | - |
| 1 | `tokens.py`, `ast_nodes.py` 스텁 작성 | O ("공통 인터페이스 스텁 추가") | X |
| 2 | RED: `test_checker.py` 작성, 실행 → 전부 실패 확인 | O ("Checker 실패 테스트 작성 (TDD red)") | **O — pytest 실패 결과 터미널 캡처** |
| 3 | GREEN: `checker.py` 최소 구현 → 테스트 전부 통과 | O ("Checker 최소 구현 (TDD green)") | **O — pytest 전체 통과 결과 캡처** |
| 4 | REFACTOR: 코드 정리 (통과 유지) | O ("Checker 리팩토링") | **O — 리팩토링 전/후 코드 diff 캡처 (발표 필수 항목)** |
| 5 | 엣지케이스 보강 (중첩스코프 등 커버리지 확인) | O (필요시) | X |
| 6 | `feature/checker` push, PR 생성 → 팀원 리뷰 요청 | - | **O — PR 화면 + 리뷰 코멘트 캡처** |
| 7 | 전체 파이프라인(prompt_shell.py) 통합 후 `테스트 스크립트.md` 전체 시나리오 데모 | - | **O — 데모 실행 결과 캡처** |

- 리팩토링 전/후 커밋은 반드시 분리 (가이드 12장 개발규칙 4번: "리팩토링 전/후 Commit 필수").
- 커밋/push/PR 생성은 매번 실행 직전 사용자에게 타이밍을 알리고 확인받는다 (되돌리기 어려운 공유 작업이므로).

## 파일 구조
```
project/
├── tokens.py          # TokenType, Token, KEYWORDS   (스텁, Assembler팀 완성 시 교체)
├── ast_nodes.py        # Expr / Stmt 노드 클래스        (스텁, Assembler팀 완성 시 교체)
├── checker.py          # Checker, CheckError            (권은재 — 본인 담당)
├── test_checker.py      # Checker 단위 테스트 (TDD)
```

## 최종 목표
`테스트 스크립트.md`의 모든 시나리오가 전체 파이프라인(Tokenizer→Parser→Checker→Executor)을
통과하는 것. Checker 담당자로서는 위 "내 판단" 절의 테스트 범위를 만족시키고,
다른 유닛과의 인터페이스(list[Stmt] 입력, None 반환, CheckError 발생)를 정확히 지키는 것이 목표.
