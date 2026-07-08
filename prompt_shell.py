from interpreter.ast_nodes import BlockStmt, ForStmt, IfStmt, Stmt
from interpreter.codefab import CodeFabInterpreter
from interpreter.errors import CheckError, CodeFabRuntimeError, ParseError, TokenizeError
from interpreter.parser import Parser
from interpreter.tokenizer import Tokenizer


def run(interpreter: CodeFabInterpreter, source: str) -> None:
    try:
        interpreter.run(source)
    except (TokenizeError, ParseError, CheckError, CodeFabRuntimeError) as e:
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


def _dangles(stmt: Stmt) -> bool:
    """이 문장 뒤에 아직 'else'가 이어붙을 수 있는 상태인지 판단한다.

    else는 항상 가장 가까운 if에 결합되므로, 마지막 문장을 따라 내려가며
    본다. '{ }' 블록으로 감싼 else 없는 if만 대상으로 한다 — 중괄호 없는
    한 줄짜리 if(예: "if (x) print 1;")는 파이썬 셸의 한 줄 if처럼 즉시
    실행되어야 하므로 제외한다.
    """
    if isinstance(stmt, IfStmt):
        if stmt.else_branch is None:
            return isinstance(stmt.then_branch, BlockStmt)
        return _dangles(stmt.else_branch)
    if isinstance(stmt, ForStmt):
        return _dangles(stmt.body)
    return False


def _waiting_for_else(source: str) -> bool:
    """지금까지 모은 입력의 마지막 문장이, else를 기다려야 하는 '{ }' if인지 확인한다.

    실제로 tokenize+parse를 시도해보고 판단한다 (부작용 없음).
    """
    try:
        tokens = Tokenizer(source).tokenize()
        statements = Parser(tokens).parse()
    except (TokenizeError, ParseError):
        return False

    return bool(statements) and _dangles(statements[-1])


def main() -> None:
    interpreter = CodeFabInterpreter()
    buffer = ""
    waiting_for_else = False  # else가 이어붙을 수 있는 if 블록이 방금 끝나서 확정을 기다리는 중인지
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
            waiting_for_else = False
            continue

        if not buffer and line.strip() in EXIT_COMMANDS:
            break

        if waiting_for_else and line.strip() == "":
            # 빈 줄(Ctrl+Enter) — 파이썬 셸처럼 여기서 입력을 확정하고 실행
            run(interpreter, buffer)
            buffer = ""
            waiting_for_else = False
            continue

        buffer = f"{buffer}\n{line}" if buffer else line
        waiting_for_else = False

        if _needs_more_input(buffer):
            continue  # 아직 문장이 안 끝났으니 '...' 프롬프트로 계속 이어받기

        if _waiting_for_else(buffer):
            waiting_for_else = True
            continue  # else가 더 붙을 수 있으니 빈 줄이 올 때까지 '...' 프롬프트로 대기

        run(interpreter, buffer)
        buffer = ""


if __name__ == "__main__":
    main()
