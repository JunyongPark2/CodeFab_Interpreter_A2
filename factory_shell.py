import os
import sys

from interpreter.codefab import CodeFabInterpreter
from interpreter.errors import CheckError, CodeFabRuntimeError, ParseError, TokenizeError
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
    except (TokenizeError, ParseError, CheckError, CodeFabRuntimeError) as e:
        print(e)
        sys.exit(1)


def run_debug_mode(path: str) -> None:
    """디버그 모드: `python factory_shell.py debug <path>`.

    TODO: Executor에 stmt 단위 훅을 연결해 step/next/break/continue/watch/inspect
    등의 stepping 명령을 처리하는 디버거를 구현한다 (5-6 디버그 모드 스펙).
    """
    raise NotImplementedError("디버그 모드는 아직 구현되지 않았습니다.")


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv

    if not args:        # 아무 인자도 주어지지 않았을 경우 REPL 실행
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
