# prompt_shell.py — CLI 기반 Prompt Shell 진입점
#
# 한 줄 입력 → CodeFabInterpreter(Assembler → Checker → Executor) → 즉시 실행
#
# 실행: python prompt_shell.py

from interpreter.codefab import (
    CheckError,
    CodeFabInterpreter,
    LangRuntimeError,
    ParseError,
    TokenizeError,
)
from interpreter.parser import Parser
from interpreter.tokenizer import Tokenizer


def run(interpreter: CodeFabInterpreter, source: str) -> None:
    try:
        interpreter.run(source)
    except (TokenizeError, ParseError, CheckError, LangRuntimeError) as e:
        print(e)


EXIT_COMMANDS = {"exit", "exit()", "quit", "quit()"}


def _needs_more_input(source: str) -> bool:
    """지금까지 모은 입력이 "문법적으로 틀리지 않은, 아직 안 끝난" 상태인지 판단한다.

    실제로 tokenize+parse를 시도해보고(부작용 없음 — check/execute는 안 함),
    ParseError.incomplete로 판단한다
    """
    try:
        tokens = Tokenizer(source).tokenize()
    except TokenizeError:
        return False

    try:
        Parser(tokens).parse()
    except ParseError as e:
        return e.incomplete
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
