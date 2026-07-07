# prompt_shell.py — CLI 기반 Prompt Shell 진입점
#
# 한 줄 입력 → CodeFabInterpreter(Assembler → Checker → Executor) → 즉시 실행
#
# 실행: python prompt_shell.py

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


def main() -> None:
    interpreter = CodeFabInterpreter()
    while True:
        try:
            source = input(">> ")
        except EOFError:
            # Ctrl+D(Unix) / Ctrl+Z+Enter(Windows) — 파이썬 셸과 동일하게 종료
            print()
            break
        except KeyboardInterrupt:
            # Ctrl+C — 파이썬 셸처럼 현재 입력만 취소하고 새 프롬프트로
            print()
            continue

        if source.strip() in EXIT_COMMANDS:
            break

        run(interpreter, source)


if __name__ == "__main__":
    main()
