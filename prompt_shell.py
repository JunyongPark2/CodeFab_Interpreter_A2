# prompt_shell.py — CLI 기반 Prompt Shell 진입점
#
# 한 줄 입력 → CodeFabInterpreter(Assembler → Checker → Executor) → 즉시 실행
#
# 실행: python prompt_shell.py

from interpreter.assembler import Assembler
from interpreter.codefab import (
    CodeFabInterpreter,
    TokenizeError,
    ParseError,
    CheckError,
    LangRuntimeError,
)


def run(interpreter: CodeFabInterpreter, source: str) -> None:
    try:
        interpreter.run(source)
    except (TokenizeError, ParseError, CheckError, LangRuntimeError) as e:
        print(e)


EXIT_COMMANDS = {"exit", "exit()", "quit", "quit()"}


def _needs_more_input(source: str) -> bool:
    """지금까지 모은 입력을 tokenize+parse만 해보고, "토큰이 부족해서(EOF)"
    실패했으면 True — 아직 문장이 안 끝났으니 다음 줄을 더 받아야 한다는 뜻.

    Assembler.assemble()은 tokenize+parse만 하고 check/execute는 하지 않으므로
    부작용(변수 선언, print 등) 없이 안전하게 "미리 살펴볼" 수 있다.
    진짜 문법 오류(예: 잘못된 토큰)는 at_eof=False이므로 더 기다리지 않고
    바로 실행 단계로 넘겨서 에러를 보여준다.
    """
    try:
        Assembler().assemble(source)
    except ParseError as e:
        return e.at_eof
    except TokenizeError:
        return False
    return False


def main() -> None:
    interpreter = CodeFabInterpreter()
    buffer = ""
    while True:
        prompt = "... " if buffer else ">> "
        try:
            line = input(prompt)
        except EOFError:
            # Ctrl+D(Unix) / Ctrl+Z+Enter(Windows) — 파이썬 셸과 동일하게 종료
            print()
            break
        except KeyboardInterrupt:
            # Ctrl+C — 파이썬 셸처럼 현재 입력(이어받던 블록 포함)만 취소하고 새 프롬프트로
            print()
            buffer = ""
            continue

        if not buffer and line.strip() in EXIT_COMMANDS:
            break

        buffer = f"{buffer}\n{line}" if buffer else line

        if _needs_more_input(buffer):
            continue  # 아직 문장이 안 끝났으니 '...' 프롬프트로 계속 이어받기

        run(interpreter, buffer)
        buffer = ""


if __name__ == "__main__":
    main()
