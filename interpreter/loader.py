import os
from contextlib import contextmanager

from .assembler import Assembler
from .ast_nodes import FuncDeclStmt, ImportStmt, Stmt, VarDeclStmt
from .errors import ModuleImportError

# import되는 파일의 최상위에는 선언(다른 파일 import / 함수 선언 / 전역 변수 선언)만
# 허용한다 (PDF 세부규칙 1). 그 외 구문 처리는 팀 자율이라고 명시되어 있어, 명확한
# 오류로 처리하는 쪽을 택했다 — 조용히 무시하면 실행 순서가 파일마다 달라져 디버깅이
# 어려워지기 때문.
_ALLOWED_TOP_LEVEL_STMTS = (ImportStmt, FuncDeclStmt, VarDeclStmt)


class Loader:
    """import 문이 가리키는 파일을 읽어 AST로 변환한다.

    "경로 -> list[Stmt]" 변환과 순환 import 탐지만 책임지고, 실제로 그 AST를
    실행해서 모듈 값(LangModule)을 만드는 건 Executor(_exec_import)가 담당한다.
    """

    def __init__(self, assembler: Assembler):
        self._assembler = assembler
        self._loading: set[str] = set()  # 현재 로딩 중인 경로 스택 (순환 import 탐지용)

    @contextmanager
    def loading(self, path: str, line: int):
        """path를 "로딩 중"으로 표시한다. 순환 import 탐지 구간은 파싱뿐 아니라
        (재귀적으로 그 파일을 import하는 문장까지 포함한) 실행 전체를 감싸야 하므로,
        호출자(Executor._exec_import)가 로드+실행을 이 컨텍스트 안에서 수행해야 한다.
        여기서 discard만 하고 load()에서 곧장 빠지면, 그 파일의 실행이 끝나기도 전에
        "로딩 끝났음"으로 표시돼 순환을 못 잡는다."""
        if path in self._loading:
            raise ModuleImportError(line, f"순환 import가 감지되었습니다: '{path}'")
        self._loading.add(path)
        try:
            yield
        finally:
            self._loading.discard(path)

    def load(self, path: str, line: int) -> list[Stmt]:
        if not os.path.exists(path):
            raise ModuleImportError(line, f"import 대상 파일이 없습니다: '{path}'")

        source = open(path, encoding="utf-8").read()
        stmts = self._assembler.assemble(source)
        self._check_only_declarations(stmts, line)
        return stmts

    def _check_only_declarations(self, stmts: list[Stmt], line: int) -> None:
        for stmt in stmts:
            if not isinstance(stmt, _ALLOWED_TOP_LEVEL_STMTS):
                raise ModuleImportError(
                    line,
                    "import 대상 파일에는 선언(import/함수 선언/전역 변수 선언)만 "
                    "작성할 수 있습니다.",
                )
