import pytest

from interpreter.assembler import Assembler
from interpreter.debugger import (
    DebugController,
    DebugExit,
    get_expr_line,
    get_stmt_line,
    stringify,
    type_name,
)
from interpreter.environment import Environment


def parse(source: str):
    return Assembler().assemble(source)


class _FakeExecutor:
    def __init__(self, env: Environment):
        self.current_env = env


# ── get_stmt_line ────────────────────────────────────────────


def test_get_stmt_line_for_var_decl():
    [stmt] = parse("var a = 1;")
    assert get_stmt_line(stmt) == 1


def test_get_stmt_line_for_print_on_later_line():
    [stmt] = parse("\n\nprint 1 + 2;")
    assert get_stmt_line(stmt) == 3


def test_get_stmt_line_for_if_uses_condition_line():
    [stmt] = parse("if (true) { print 1; }")
    assert get_stmt_line(stmt) == 1


def test_get_stmt_line_for_block_uses_first_inner_statement_line():
    [stmt] = parse("{\n    var a = 1;\n}")
    assert get_stmt_line(stmt) == 2


def test_get_stmt_line_for_empty_block_is_zero():
    [stmt] = parse("{}")
    assert get_stmt_line(stmt) == 0


def test_get_stmt_line_for_return():
    [stmt] = parse("return 1;")
    assert get_stmt_line(stmt) == 1


def test_get_stmt_line_for_class_decl():
    [stmt] = parse("Class Foo {}")
    assert get_stmt_line(stmt) == 1


def test_get_stmt_line_for_import():
    [stmt] = parse('import "x.txt" alias x;')
    assert get_stmt_line(stmt) == 1


def test_get_stmt_line_for_for_uses_initializer_line():
    [stmt] = parse("\nfor (var i = 0; i < 3; i = i + 1) { print i; }")
    assert get_stmt_line(stmt) == 2


def test_get_stmt_line_for_for_without_initializer_uses_condition_line():
    [stmt] = parse("\nfor (; i < 3; i = i + 1) { print i; }")
    assert get_stmt_line(stmt) == 2


def test_get_stmt_line_for_bare_for_uses_body_line():
    [stmt] = parse("\nfor (;;) { print 1; }")
    assert get_stmt_line(stmt) == 2


def test_get_stmt_line_for_func_decl():
    [stmt] = parse("Func foo() {}")
    assert get_stmt_line(stmt) == 1


def test_get_stmt_line_for_unhandled_stmt_type_is_zero():
    class _UnknownStmt:
        pass

    assert get_stmt_line(_UnknownStmt()) == 0


# ── get_expr_line ────────────────────────────────────────────


@pytest.mark.parametrize(
    "source",
    [
        "print -1;",
        "print (1 + 2);",
        "print true and false;",
        "foo();",
        "print obj.field;",
        "obj.field = 1;",
        "print This;",
        "Super.move();",
        "print x instanceof Foo;",
        "print arr[0];",
        "arr[0] = 1;",
        "print Array(3);",
        "a = 1;",
    ],
)
def test_get_stmt_line_resolves_expr_line_via_wrapping_stmt(source):
    [stmt] = parse("\n" + source)  # 2번째 줄에 실제 코드를 두어 기본값(0)과 구분한다
    assert get_stmt_line(stmt) == 2


def test_get_expr_line_for_unhandled_expr_type_is_zero():
    class _UnknownExpr:
        pass

    assert get_expr_line(_UnknownExpr()) == 0


# ── stringify / type_name ────────────────────────────────────


def test_stringify_matches_executor_style_formatting():
    assert stringify(None) == "null"
    assert stringify(True) == "true"
    assert stringify(3.0) == "3"
    assert stringify([1.0, 2.0]) == "[1, 2]"


def test_type_name_reports_expected_labels():
    assert type_name(None) == "Null"
    assert type_name(True) == "Boolean"
    assert type_name(3.0) == "Number"
    assert type_name("hi") == "String"
    assert type_name([1.0]) == "Array"


def test_stringify_falls_back_to_str_for_unknown_value():
    class _Custom:
        def __str__(self):
            return "<custom>"

    assert stringify(_Custom()) == "<custom>"


def test_type_name_falls_back_to_python_type_name_for_unknown_value():
    class _Custom:
        pass

    assert type_name(_Custom()) == "_Custom"


# ── DebugController ──────────────────────────────────────────


def test_first_statement_always_pauses_without_any_command_yet(monkeypatch, capsys):
    source = "var a = 0;\n"
    [stmt] = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    monkeypatch.setattr("builtins.input", lambda prompt="": "continue")
    controller.on_stmt(stmt, 0, fake)

    assert "1번째 줄에서 정지 → var a = 0;" in capsys.readouterr().out


def test_breakpoint_pauses_regardless_of_continue_mode(monkeypatch, capsys):
    source = "var a = 0;\nvar b = 1;\nvar c = 2;\n"
    stmts = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["break 3", "continue", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    for stmt in stmts:
        controller.on_stmt(stmt, 0, fake)

    out = capsys.readouterr().out
    assert "1번째 줄에서 정지 → var a = 0;" in out
    assert "3번째 줄에 breakpoint 설정" in out
    assert "3번째 줄에서 정지 → var c = 2;" in out
    assert "2번째 줄에서 정지" not in out


def test_remove_breakpoint_stops_it_from_pausing(monkeypatch, capsys):
    source = "var a = 0;\nvar b = 1;\n"
    stmts = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["break 2", "remove 2", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    for stmt in stmts:
        controller.on_stmt(stmt, 0, fake)

    out = capsys.readouterr().out
    assert "2번째 줄의 breakpoint 해제" in out
    assert "2번째 줄에서 정지" not in out


def test_next_mode_does_not_pause_at_deeper_depth(monkeypatch, capsys):
    source = "var a = 0;\nvar b = 1;\nvar c = 2;\n"
    stmts = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["next", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmts[0], 0, fake)  # pauses (default "step"), user issues "next"
    controller.on_stmt(stmts[1], 1, fake)  # deeper than target depth -> must not pause
    controller.on_stmt(stmts[2], 0, fake)  # back at target depth -> pauses again

    out = capsys.readouterr().out
    assert out.count("정지 →") == 2
    assert "2번째 줄에서 정지" not in out


def test_watch_prints_value_on_next_pause(monkeypatch, capsys):
    source = "var a = 1;\nvar b = 2;\n"
    stmts = parse(source)
    controller = DebugController(source)
    env = Environment()
    env.define("a", 1.0)
    fake = _FakeExecutor(env)

    commands = iter(["watch a", "step", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmts[0], 0, fake)
    controller.on_stmt(stmts[1], 0, fake)

    out = capsys.readouterr().out
    assert "[WATCH] 'a' 감시 등록" in out
    assert "[WATCH] a = 1" in out


def test_unwatch_removes_variable_from_watch_list(monkeypatch, capsys):
    source = "var a = 1;\nvar b = 2;\n"
    stmts = parse(source)
    controller = DebugController(source)
    env = Environment()
    env.define("a", 1.0)
    fake = _FakeExecutor(env)

    commands = iter(["watch a", "unwatch a", "step", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmts[0], 0, fake)
    controller.on_stmt(stmts[1], 0, fake)

    out = capsys.readouterr().out
    assert "[WATCH] 'a' 감시 해제" in out
    assert "[WATCH] a = 1" not in out


def test_watches_lists_currently_watched_variables(monkeypatch, capsys):
    source = "var a = 1;\n"
    [stmt] = parse(source)
    controller = DebugController(source)
    env = Environment()
    env.define("a", 5.0)
    fake = _FakeExecutor(env)

    commands = iter(["watch a", "watches", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmt, 0, fake)

    out = capsys.readouterr().out
    assert out.count("[WATCH] a = 5") == 1  # 등록 시 한 번, watches 명령으로 또 한 번은 안 됨


def test_inspect_prints_local_and_global_scope_variables(monkeypatch, capsys):
    source = "var a = 1;\n"
    [stmt] = parse(source)
    controller = DebugController(source)

    global_env = Environment()
    global_env.define("g", True)
    local_env = Environment(parent=global_env)
    local_env.define("x", 10.0)
    fake = _FakeExecutor(local_env)

    commands = iter(["inspect", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmt, 0, fake)

    out = capsys.readouterr().out
    assert "[로컬] x = 10 (Number)" in out
    assert "[전역] g = true (Boolean)" in out


def test_breakpoints_command_lists_registered_breakpoints(monkeypatch, capsys):
    source = "var a = 1;\n"
    [stmt] = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["break 5", "breakpoints", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmt, 0, fake)

    out = capsys.readouterr().out
    assert "[BREAKPOINT] 5번째 줄" in out


def test_breakpoints_command_reports_when_none_registered(monkeypatch, capsys):
    source = "var a = 1;\n"
    [stmt] = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["breakpoints", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmt, 0, fake)

    assert "[BREAKPOINT] 설정된 breakpoint가 없습니다." in capsys.readouterr().out


def test_watches_command_reports_when_none_registered(monkeypatch, capsys):
    source = "var a = 1;\n"
    [stmt] = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["watches", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmt, 0, fake)

    assert "[WATCH] 감시 중인 변수가 없습니다." in capsys.readouterr().out


def test_watch_on_undefined_variable_is_silently_skipped(monkeypatch, capsys):
    source = "var a = 1;\nvar b = 2;\n"
    stmts = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())  # 'not_defined_yet'는 존재하지 않는다

    commands = iter(["watch not_defined_yet", "step", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmts[0], 0, fake)
    controller.on_stmt(stmts[1], 0, fake)

    out = capsys.readouterr().out
    assert "[WATCH] 'not_defined_yet' 감시 등록" in out
    assert "[WATCH] not_defined_yet =" not in out


def test_command_loop_treats_eof_as_continue(monkeypatch, capsys):
    source = "var a = 1;\nvar b = 2;\n"
    stmts = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    def _raise_eof(prompt=""):
        raise EOFError()

    monkeypatch.setattr("builtins.input", _raise_eof)

    controller.on_stmt(stmts[0], 0, fake)  # EOF 취급 -> mode를 "continue"로 바꾸고 재개
    controller.on_stmt(stmts[1], 0, fake)  # breakpoint도 없으므로 더 이상 멈추지 않는다

    out = capsys.readouterr().out
    assert out.count("정지 →") == 1


def test_source_line_text_out_of_range_returns_empty_string():
    controller = DebugController("var a = 1;\n")
    assert controller._source_line_text(999) == ""
    assert controller._source_line_text(0) == ""


@pytest.mark.parametrize("keyword", ["exit", "exit()", "quit", "quit()"])
def test_exit_and_quit_raise_debug_exit(monkeypatch, capsys, keyword):
    source = "var a = 1;\nvar b = 2;\n"
    stmts = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    monkeypatch.setattr("builtins.input", lambda prompt="": keyword)

    with pytest.raises(DebugExit):
        controller.on_stmt(stmts[0], 0, fake)

    assert "디버그 세션을 종료합니다" in capsys.readouterr().out


def test_exit_commands_match_prompt_shell():
    import prompt_shell
    from interpreter import debugger

    assert debugger.EXIT_COMMANDS is prompt_shell.EXIT_COMMANDS


def test_blank_command_is_ignored_and_reprompts(monkeypatch, capsys):
    source = "var a = 1;\n"
    [stmt] = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["", "   ", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmt, 0, fake)  # 예외 없이 "continue"까지 도달해야 한다


def test_unknown_command_prints_hint_and_reprompts(monkeypatch, capsys):
    source = "var a = 1;\n"
    [stmt] = parse(source)
    controller = DebugController(source)
    fake = _FakeExecutor(Environment())

    commands = iter(["nonsense", "continue"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(commands))

    controller.on_stmt(stmt, 0, fake)

    assert "알 수 없는 명령어" in capsys.readouterr().out
