import os
import sys

from interpreter.assembler import Assembler
from interpreter.checker import Checker
from interpreter.codefab import CodeFabInterpreter
from interpreter.debugger import DebugController, DebugExit
from interpreter.errors import (
    CheckError,
    CodeFabRuntimeError,
    ModuleImportError,
    ParseError,
    TokenizeError,
)
from interpreter.executor import Executor
from interpreter.loader import Loader
from prompt_shell import main as run_repl_mode

USAGE = "사용법: factory_shell.py [run|debug] <파일경로>"


def run_file_mode(path: str) -> None:
    """파일 모드: `python factory_shell.py run <path>`."""
    if not os.path.exists(path):
        print(f"파일을 찾을 수 없습니다: '{path}'")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        source = f.read()

    try:
        CodeFabInterpreter().run(source)
    except (
        TokenizeError,
        ParseError,
        CheckError,
        CodeFabRuntimeError,
        ModuleImportError,
    ) as e:
        print(e)
        sys.exit(1)


def run_debug_mode(path: str) -> None:
    """디버그 모드: `python factory_shell.py debug <path>`.

    소스를 Stmt 단위로 멈춰가며 실행 상태를 점검한다 (step/next/break/continue/
    watch/inspect). Stepping 자체는 DebugController가 Executor의 on_stmt 훅으로
    꽂혀서 처리하고, 여기서는 파이프라인 연결과 파일/파싱 오류 처리만 담당한다.
    """
    if not os.path.exists(path):
        print(f"파일을 찾을 수 없습니다: '{path}'")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        source = f.read()

    print(f"[DEBUG] 소스코드 로딩: {path}")

    assembler = Assembler()
    try:
        stmts = assembler.assemble(source)
        locals_map = Checker(stmts).check()
    except (TokenizeError, ParseError, CheckError) as e:
        print(e)
        sys.exit(1)

    controller = DebugController(source)
    executor = Executor(
        stmts,
        locals=locals_map,
        loader=Loader(assembler),
        on_stmt=controller.on_stmt,
        source=source,
        path=path,
    )

    try:
        executor.execute()
    except DebugExit:
        return
    except (
        TokenizeError,
        ParseError,
        CheckError,
        CodeFabRuntimeError,
        ModuleImportError,
    ) as e:
        print(e)
        sys.exit(1)

    print("[DEBUG] 실행이 종료되었습니다.")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv

    if not args:  # 아무 인자도 주어지지 않았을 경우 REPL 실행
        run_repl_mode()
    elif args[0] == "run" and len(args) == 2:
        run_file_mode(args[1])
    elif args[0] == "debug" and len(args) == 2:
        run_debug_mode(args[1])
    else:
        print(USAGE)
        sys.exit(1)


if __name__ == "__main__":
    main()
