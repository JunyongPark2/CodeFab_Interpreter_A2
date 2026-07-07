from .assembler import Assembler
from .checker import Checker, CheckError
from .executor import Executor, LangRuntimeError
from .tokenizer import TokenizeError
from .parser import ParseError


class CodeFabInterpreter:
    """source str → Assemble → Check → Execute 파이프라인."""

    def __init__(self):
        self._assembler = Assembler()

    def run(self, source: str) -> None:
        stmts = self._assembler.assemble(source)
        Checker(stmts).check()
        Executor(stmts).execute()
