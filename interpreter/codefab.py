from .assembler import Assembler
from .checker import Checker, CheckError
from .executor import Environment, Executor, LangRuntimeError
from .tokenizer import TokenizeError
from .parser import ParseError


class CodeFabInterpreter:
    """source str → Assemble → Check → Execute 파이프라인.

    Prompt Shell처럼 한 줄씩 여러 번 run()이 호출되는 상황을 위해
    전역 Environment를 인스턴스에 보관하고 매 run()마다 재사용한다.
    그래야 이전 줄에서 선언한 변수를 다음 줄에서도 계속 쓸 수 있다.
    """

    def __init__(self):
        self._assembler = Assembler()
        self._global_env = Environment()

    def run(self, source: str) -> None:
        stmts = self._assembler.assemble(source)
        Checker(stmts).check()
        Executor(stmts, environment=self._global_env).execute()
