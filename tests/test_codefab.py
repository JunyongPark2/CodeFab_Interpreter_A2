import pytest

from interpreter.checker import CheckError
from interpreter.codefab import CodeFabInterpreter
from interpreter.executor import LangRuntimeError
from interpreter.parser import ParseError
from interpreter.tokenizer import TokenizeError


@pytest.fixture
def interp():
    return CodeFabInterpreter()


# ── 정상 출력 ──────────────────────────────────────────────────────

def test_print_integer(interp, capsys):
    interp.run("print 42;")
    assert capsys.readouterr().out == "42\n"


def test_print_float(interp, capsys):
    interp.run("print 3.14;")
    assert capsys.readouterr().out == "3.14\n"


def test_print_string(interp, capsys):
    interp.run('print "hello";')
    assert capsys.readouterr().out == "hello\n"


def test_print_bool_true(interp, capsys):
    interp.run("print true;")
    assert capsys.readouterr().out == "true\n"


def test_print_bool_false(interp, capsys):
    interp.run("print false;")
    assert capsys.readouterr().out == "false\n"


# ── 변수 선언 / 재할당 ────────────────────────────────────────────

def test_var_decl_and_print(interp, capsys):
    interp.run("var x = 10; print x;")
    assert capsys.readouterr().out == "10\n"


def test_var_reassign(interp, capsys):
    interp.run("var x = 1; x = 99; print x;")
    assert capsys.readouterr().out == "99\n"


def test_var_without_initializer_is_nil(interp, capsys):
    interp.run("var x; print x;")
    assert capsys.readouterr().out == "nil\n"


# ── 산술 ──────────────────────────────────────────────────────────

def test_arithmetic_expression(interp, capsys):
    interp.run("print 2 + 3 * 4;")
    assert capsys.readouterr().out == "14\n"


def test_string_concatenation(interp, capsys):
    interp.run('print "foo" + "bar";')
    assert capsys.readouterr().out == "foobar\n"


# ── 블록 / 스코프 ─────────────────────────────────────────────────

def test_block_scope_shadowing(interp, capsys):
    interp.run('var x = "outer"; { var x = "inner"; print x; } print x;')
    assert capsys.readouterr().out == "inner\nouter\n"


def test_block_mutates_outer_variable(interp, capsys):
    interp.run("var n = 0; { n = 5; } print n;")
    assert capsys.readouterr().out == "5\n"


# ── if / else ────────────────────────────────────────────────────

def test_if_true_branch(interp, capsys):
    interp.run('if (true) print "yes";')
    assert capsys.readouterr().out == "yes\n"


def test_if_false_runs_else(interp, capsys):
    interp.run('if (false) print "yes"; else print "no";')
    assert capsys.readouterr().out == "no\n"


# ── for 루프 ──────────────────────────────────────────────────────

def test_for_loop(interp, capsys):
    interp.run("for (var i = 0; i < 3; i = i + 1) print i;")
    assert capsys.readouterr().out == "0\n1\n2\n"


# ── 주석 ──────────────────────────────────────────────────────────

def test_line_comment_is_ignored(interp, capsys):
    interp.run("// this is a comment\nprint 1;")
    assert capsys.readouterr().out == "1\n"


# ── TokenizeError ─────────────────────────────────────────────────

def test_unknown_character_raises_tokenize_error(interp):
    with pytest.raises(TokenizeError):
        interp.run("print @;")


def test_unterminated_string_raises_tokenize_error(interp):
    with pytest.raises(TokenizeError):
        interp.run('print "unclosed;')


# ── ParseError ────────────────────────────────────────────────────

def test_missing_semicolon_raises_parse_error(interp):
    with pytest.raises(ParseError):
        interp.run("print 1")


def test_unmatched_paren_raises_parse_error(interp):
    with pytest.raises(ParseError):
        interp.run("print (1 + 2;")


# ── CheckError ────────────────────────────────────────────────────

def test_duplicate_var_in_same_scope_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("{ var a = 1; var a = 2; }")


def test_self_reference_in_initializer_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("{ var a = a; }")


# ── LangRuntimeError ──────────────────────────────────────────────

def test_undefined_variable_raises_runtime_error(interp):
    with pytest.raises(LangRuntimeError):
        interp.run("print x;")


def test_division_by_zero_raises_runtime_error(interp):
    with pytest.raises(LangRuntimeError):
        interp.run("print 1 / 0;")


def test_type_mismatch_raises_runtime_error(interp):
    with pytest.raises(LangRuntimeError):
        interp.run('print 1 - "a";')


# ── 상태 공유: 여러 번 run() 해도 전역 환경 유지 ────────────────────

def test_runs_share_global_env(interp, capsys):
    interp.run("var x = 10;")
    interp.run("print x;")
    assert capsys.readouterr().out == "10\n"


def test_global_var_redeclaration_across_runs_raises_check_error(interp):
    interp.run("var x = 10;")
    with pytest.raises(CheckError):
        interp.run("var x = 20;")


def test_global_var_reassignment_across_runs_is_allowed(interp, capsys):
    interp.run("var x = 10;")
    interp.run("x = 99; print x;")
    assert capsys.readouterr().out == "99\n"


def test_multiple_global_vars_across_runs(interp, capsys):
    interp.run("var a = 1; var b = 2;")
    interp.run("print a + b;")
    assert capsys.readouterr().out == "3\n"


def test_global_var_redeclaration_in_single_run_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("var x = 1; var x = 2;")


def test_for_loop_var_does_not_leak_into_global_scope(interp, capsys):
    interp.run("for (var i = 0; i < 3; i = i + 1) { print i; }")
    capsys.readouterr()
    interp.run("var i = 5; print i;")
    assert capsys.readouterr().out == "5\n"


# ── 이중 for 루프 ──────────────────────────────────────────────────

def test_nested_for_loop(interp, capsys):
    interp.run("for (var i = 0; i < 2; i = i + 1) { for (var j = 0; j < 2; j = j + 1) { print i + j; } }")
    assert capsys.readouterr().out == "0\n1\n1\n2\n"


def test_nested_for_loop_vars_do_not_leak_into_global_scope(interp, capsys):
    interp.run("for (var i = 0; i < 2; i = i + 1) { for (var j = 0; j < 2; j = j + 1) { print i + j; } }")
    capsys.readouterr()
    interp.run("var i = 10; var j = 20; print i + j;")
    assert capsys.readouterr().out == "30\n"


def test_nested_for_loop_same_var_shadowing(interp, capsys):
    interp.run("for (var i = 0; i < 2; i = i + 1) { for (var i = 10; i < 12; i = i + 1) { print i; } }")
    assert capsys.readouterr().out == "10\n11\n10\n11\n"
