import pytest

from interpreter.assembler import Assembler
from interpreter.ast_nodes import ImportStmt, LiteralExpr, VarDeclStmt
from interpreter.codefab import CodeFabInterpreter
from interpreter.errors import CodeFabRuntimeError, ModuleImportError
from interpreter.executor import Executor
from interpreter.loader import Loader
from interpreter.runtime import CodeFabFunction, CodeFabModule
from tests.helpers import name_tok, path_tok

# ── Executor 단독 단위 테스트 (Loader를 직접 주입) ──────────────


def test_import_without_loader_raises_runtime_error():
    stmt = ImportStmt(path_tok("sum.txt"), name_tok("sum"))
    with pytest.raises(CodeFabRuntimeError, match="import를 사용할 수 없습니다"):
        Executor([stmt]).execute()


def test_import_defines_alias_as_codefab_module(tmp_write):
    path = tmp_write("sum.txt", "Func add(a, b) { return a + b; }\nvar VERSION = 1;\n")
    stmt = ImportStmt(path_tok(path), name_tok("sum"))
    loader = Loader(Assembler())

    executor = Executor([stmt], loader=loader)
    executor.execute()

    module = executor._global.get("sum")
    assert isinstance(module, CodeFabModule)
    assert module.name == "sum"
    assert set(module.fields.keys()) == {"add", "VERSION"}
    assert isinstance(module.fields["add"], CodeFabFunction)
    assert module.fields["VERSION"] == 1.0


def test_module_environment_is_isolated_from_importing_scope(tmp_write):
    # 모듈 파일 안에서 밖의(importing 쪽) 변수를 볼 수 없어야 한다 (독립된 네임스페이스).
    # outer는 실행 중인 스코프에는 존재하지만 모듈 실행 환경의 부모가 아니므로,
    # 모듈이 격리돼 있다면 그래도 "미정의된 변수" 오류가 나야 한다.
    path = tmp_write("needs_outer.txt", "var seen = outer;\n")
    loader = Loader(Assembler())
    executor = Executor(
        [
            VarDeclStmt(name_tok("outer"), LiteralExpr(1.0)),
            ImportStmt(path_tok(path), name_tok("m")),
        ],
        loader=loader,
    )
    with pytest.raises(CodeFabRuntimeError, match="미정의된 변수 'outer'"):
        executor.execute()


def test_module_loader_error_propagates_with_line_number():
    stmt = ImportStmt(path_tok("없는파일.txt", line=7), name_tok("m"))
    loader = Loader(Assembler())
    with pytest.raises(ModuleImportError, match=r"\[7번째줄\]"):
        Executor([stmt], loader=loader).execute()


# ── CodeFabInterpreter 전체 파이프라인 end-to-end ────────────────


def test_end_to_end_import_via_codefab_interpreter(tmp_write, capsys):
    path = tmp_write("sum.txt", "Func add(a, b) { return a + b; }\n")
    interp = CodeFabInterpreter()
    interp.run(f'import "{path}" alias sum;\n')

    module = interp._global_env.get("sum")
    assert isinstance(module, CodeFabModule)
    # `.` 문법(GetExpr)은 Class 기능이 들어와야 파싱/실행되므로, 지금은 CodeFabFunction을
    # 직접 꺼내 실행기 내부 API로 호출해서 모듈이 올바르게 구성됐는지만 검증한다.
    add_fn = module.fields["add"]
    result = add_fn.call(Executor([]), [2.0, 3.0])
    assert result == 5.0


def test_end_to_end_circular_import_raises(tmp_path, tmp_write):
    a_path = str(tmp_path / "a.txt")
    b_path = str(tmp_path / "b.txt")
    tmp_write("a.txt", f'import "{b_path}" alias b;\n')
    tmp_write("b.txt", f'import "{a_path}" alias a;\n')

    with pytest.raises(ModuleImportError, match="순환 import"):
        CodeFabInterpreter().run(f'import "{a_path}" alias a;\n')


def test_end_to_end_missing_file_raises():
    with pytest.raises(ModuleImportError, match="파일이 없습니다"):
        CodeFabInterpreter().run('import "이런파일없음.txt" alias x;\n')


def test_end_to_end_module_with_non_declaration_statement_raises(tmp_write):
    path = tmp_write("bad.txt", 'print "hi";\n')
    with pytest.raises(ModuleImportError, match="선언"):
        CodeFabInterpreter().run(f'import "{path}" alias bad;\n')


def test_end_to_end_reimport_same_file_in_nested_scope_raises(tmp_write):
    path = tmp_write("sum.txt", "var x = 1;\n")
    src = f'import "{path}" alias sum;\n{{ import "{path}" alias sum2; }}\n'
    with pytest.raises(Exception):  # CheckError
        CodeFabInterpreter().run(src)


def test_end_to_end_import_forbidden_inside_for_loop_raises(tmp_write):
    path = tmp_write("sum.txt", "var x = 1;\n")
    src = f'for (var i = 0; i < 1; i = i + 1) {{ import "{path}" alias sum; }}\n'
    with pytest.raises(Exception):  # ParseError
        CodeFabInterpreter().run(src)


def test_end_to_end_nested_module_import_chain_works(tmp_write):
    # base.txt는 함수 하나를 정의하고, mid.txt는 base.txt를 import한다.
    base_path = tmp_write("base.txt", "Func double(n) { return n * 2; }\n")
    mid_path = tmp_write(
        "mid.txt", f'import "{base_path}" alias base;\nvar tag = "mid";\n'
    )

    interp = CodeFabInterpreter()
    interp.run(f'import "{mid_path}" alias mid;\n')

    mid_module = interp._global_env.get("mid")
    assert isinstance(mid_module, CodeFabModule)
    assert mid_module.fields["tag"] == "mid"
    base_module = mid_module.fields["base"]
    assert isinstance(base_module, CodeFabModule)
    assert isinstance(base_module.fields["double"], CodeFabFunction)


def test_end_to_end_reimporting_after_repl_line_boundary_reuses_global_env(tmp_write):
    # REPL처럼 CodeFabInterpreter.run()을 여러 줄에 걸쳐 호출해도, 이미 최상위에서
    # import한 alias 이름을 다음 줄에서 다시 import하려 하면 여전히 중복으로 잡혀야 한다.
    path = tmp_write("sum.txt", "var x = 1;\n")
    interp = CodeFabInterpreter()
    interp.run(f'import "{path}" alias sum;\n')
    with pytest.raises(Exception):  # CheckError (alias 이름 충돌)
        interp.run(f'import "{path}" alias sum;\n')


# ── `.` 문법으로 모듈 멤버 접근 (Class의 GetExpr/CallExpr 재사용) ────────────


def test_module_function_member_can_be_called_via_dot_syntax(tmp_write, capsys):
    path = tmp_write("sum.txt", "Func add(a, b) { return a + b; }\n")
    CodeFabInterpreter().run(f'import "{path}" alias sum;\nprint sum.add(1, 2);\n')
    assert capsys.readouterr().out == "3\n"


def test_module_variable_member_can_be_read_via_dot_syntax(tmp_write, capsys):
    path = tmp_write("sum.txt", "var VERSION = 1;\n")
    CodeFabInterpreter().run(f'import "{path}" alias sum;\nprint sum.VERSION;\n')
    assert capsys.readouterr().out == "1\n"


def test_accessing_nonexistent_module_member_raises(tmp_write):
    path = tmp_write("sum.txt", "var VERSION = 1;\n")
    with pytest.raises(CodeFabRuntimeError, match="'nope'"):
        CodeFabInterpreter().run(f'import "{path}" alias sum;\nprint sum.nope;\n')


def test_assigning_to_module_member_raises(tmp_write):
    # 모듈은 읽기 전용 네임스페이스로 취급한다 (sum.x = 1; 금지).
    path = tmp_write("sum.txt", "var x = 1;\n")
    with pytest.raises(CodeFabRuntimeError, match="모듈에는 값을 대입할 수 없습니다"):
        CodeFabInterpreter().run(f'import "{path}" alias sum;\nsum.x = 5;\n')


def test_nested_module_member_accessible_via_chained_dot_syntax(tmp_write, capsys):
    # mid.txt가 base.txt를 import했을 때, mid.base.double(3)처럼 체이닝도 된다
    # (GetExpr가 중첩된 CodeFabModule에도 동일하게 적용되므로).
    base_path = tmp_write("base.txt", "Func double(n) { return n * 2; }\n")
    mid_path = tmp_write("mid.txt", f'import "{base_path}" alias base;\n')

    interp = CodeFabInterpreter()
    interp.run(f'import "{mid_path}" alias mid;\n')
    interp.run("print mid.base.double(3);")
    assert capsys.readouterr().out == "6\n"
