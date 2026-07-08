import pytest

from interpreter.assembler import Assembler
from interpreter.ast_nodes import FuncDeclStmt, ImportStmt, VarDeclStmt
from interpreter.errors import ModuleImportError
from interpreter.loader import Loader


def make_loader() -> Loader:
    return Loader(Assembler())


def test_load_returns_parsed_statements(tmp_write):
    path = tmp_write("sum.txt", "Func add(a, b) { return a + b; }\nvar VERSION = 1;\n")
    stmts = make_loader().load(path, line=1)

    assert len(stmts) == 2
    assert isinstance(stmts[0], FuncDeclStmt)
    assert isinstance(stmts[1], VarDeclStmt)


def test_load_missing_file_raises():
    with pytest.raises(ModuleImportError):
        make_loader().load("이런_파일은_없다.txt", line=3)


def test_load_rejects_non_declaration_top_level_statement(tmp_write):
    path = tmp_write("bad.txt", 'print "hello";\n')
    with pytest.raises(ModuleImportError):
        make_loader().load(path, line=1)


def test_load_allows_nested_import_declaration(tmp_write):
    # import 대상 파일 안에서 또 다른 파일을 import하는 것도 "선언"으로 허용된다.
    inner = tmp_write("inner.txt", "var x = 1;\n")
    outer = tmp_write("outer.txt", f'import "{inner}" alias inner;\n')

    stmts = make_loader().load(outer, line=1)
    assert len(stmts) == 1
    assert isinstance(stmts[0], ImportStmt)


def test_load_propagates_parse_error_from_malformed_source(tmp_write):
    path = tmp_write("broken.txt", "var = ;\n")
    with pytest.raises(Exception):
        make_loader().load(path, line=1)


def test_loading_context_manager_detects_direct_cycle(tmp_path):
    path = str(tmp_path / "a.txt")
    loader = make_loader()
    with loader.loading(path, line=1):
        with pytest.raises(ModuleImportError):
            with loader.loading(path, line=2):
                pass  # 도달하면 안 됨


def test_loading_context_manager_releases_path_after_exit(tmp_path):
    path = str(tmp_path / "a.txt")
    loader = make_loader()
    with loader.loading(path, line=1):
        pass
    # 컨텍스트를 빠져나온 뒤엔 같은 경로를 다시 로딩해도 순환으로 취급하지 않는다.
    with loader.loading(path, line=1):
        pass


def test_loading_context_manager_releases_path_even_on_exception(tmp_path):
    path = str(tmp_path / "a.txt")
    loader = make_loader()
    with pytest.raises(RuntimeError):
        with loader.loading(path, line=1):
            raise RuntimeError("일부러 발생시킨 예외")

    with loader.loading(path, line=1):
        pass  # 위에서 예외가 나도 _loading에서는 제거돼야 한다
