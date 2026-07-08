import pytest

import factory_shell


def test_main_with_no_args_dispatches_to_repl_mode(monkeypatch):
    called = []
    monkeypatch.setattr(factory_shell, "run_repl_mode", lambda: called.append("repl"))
    factory_shell.main([])
    assert called == ["repl"]


def test_main_dispatches_run_to_file_mode_with_path(monkeypatch):
    called = []
    monkeypatch.setattr(factory_shell, "run_file_mode", lambda path: called.append(path))
    factory_shell.main(["run", "program.cf"])
    assert called == ["program.cf"]


def test_main_dispatches_debug_to_debug_mode_with_path(monkeypatch):
    called = []
    monkeypatch.setattr(factory_shell, "run_debug_mode", lambda path: called.append(path))
    factory_shell.main(["debug", "program.cf"])
    assert called == ["program.cf"]


@pytest.mark.parametrize(
    "argv",
    [
        ["run"],  # 경로 누락
        ["debug"],  # 경로 누락
        ["run", "a.cf", "extra"],  # 인자 초과
        ["unknown", "a.cf"],  # 알 수 없는 서브커맨드
    ],
)
def test_main_prints_usage_and_exits_on_invalid_args(monkeypatch, capsys, argv):
    with pytest.raises(SystemExit) as exc_info:
        factory_shell.main(argv)
    assert exc_info.value.code == 1
    assert capsys.readouterr().out.strip() == factory_shell.USAGE


def test_run_file_mode_exits_with_error_when_file_missing(tmp_path, capsys):
    missing = tmp_path / "does_not_exist.cf"

    with pytest.raises(SystemExit) as exc_info:
        factory_shell.run_file_mode(str(missing))

    assert exc_info.value.code == 1
    assert "찾을 수 없습니다" in capsys.readouterr().out


def test_run_file_mode_runs_source_and_exits_zero(tmp_path, capsys):
    path = tmp_path / "program.cf"
    path.write_text('print 1 + 2;', encoding="utf-8")

    factory_shell.run_file_mode(str(path))  # 정상 종료 시 sys.exit 자체를 호출하지 않는다.

    assert capsys.readouterr().out.strip() == "3"


@pytest.mark.parametrize(
    "source,expected_msg",
    [
        ("print 1 + 2", "[1번째줄] ';' 가 필요합니다."),
        ("print @;", "[1번째줄] 인식할 수 없는 문자: '@'"),
        ("print notDefined;", "[1번째줄] 미정의된 변수 'notDefined'"),
        ('{ var a = a; }', "[1번째줄] 자신의 초기화식에서 지역변수를 읽을 수 없습니다."),
    ],
)
def test_run_file_mode_prints_error_and_exits_one(tmp_path, capsys, source, expected_msg):
    path = tmp_path / "program.cf"
    path.write_text(source, encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        factory_shell.run_file_mode(str(path))

    assert exc_info.value.code == 1
    assert capsys.readouterr().out.strip() == expected_msg


def test_run_file_mode_reports_error_line_ignoring_trailing_newline(tmp_path, capsys):
    # 파일은 보통 마지막 줄 뒤에 개행이 붙어 저장된다. 그 트레일링 개행까지
    # 줄 수로 세어 EOF 토큰의 줄 번호가 실제 코드보다 한 줄 밀리면 안 된다.
    path = tmp_path / "program.cf"
    path.write_text('var a = 3;\nprint("ho")\n', encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        factory_shell.run_file_mode(str(path))

    assert exc_info.value.code == 1
    assert capsys.readouterr().out.strip() == "[2번째줄] ';' 가 필요합니다."


def test_run_file_mode_reports_error_line_where_semicolon_is_missing_mid_file(
        tmp_path, capsys
):
    # 세미콜론이 빠진 문장 다음 줄에 새 문장이 이어지는 경우, 다음 문장이
    # 시작되는 줄이 아니라 세미콜론이 빠진 실제 줄을 가리켜야 한다.
    path = tmp_path / "program.cf"
    path.write_text(
        'var a = 3;\n'
        'print("ho");\n'
        'for (var b=3; b<=10; b=b+1){\n'
        '    print("hm")\n'
        '    print("kakaka");\n'
        '}\n',
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as exc_info:
        factory_shell.run_file_mode(str(path))

    assert exc_info.value.code == 1
    assert capsys.readouterr().out.strip() == "[4번째줄] ';' 가 필요합니다."


def _feed_input(monkeypatch, commands):
    it = iter(commands)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(it))


def test_run_debug_mode_exits_with_error_when_file_missing(tmp_path, capsys):
    missing = tmp_path / "does_not_exist.cf"

    with pytest.raises(SystemExit) as exc_info:
        factory_shell.run_debug_mode(str(missing))

    assert exc_info.value.code == 1
    assert "찾을 수 없습니다" in capsys.readouterr().out


def test_run_debug_mode_prints_error_and_exits_one_on_parse_error(tmp_path, capsys):
    path = tmp_path / "program.cf"
    path.write_text("print 1 + 2", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        factory_shell.run_debug_mode(str(path))

    assert exc_info.value.code == 1
    assert "[1번째줄] ';' 가 필요합니다." in capsys.readouterr().out


def test_run_debug_mode_steps_through_every_statement(tmp_path, capsys, monkeypatch):
    path = tmp_path / "program.cf"
    path.write_text("var a = 3;\nvar b = a + 1;\nprint b;\n", encoding="utf-8")

    _feed_input(monkeypatch, ["step", "step", "step"])

    factory_shell.run_debug_mode(str(path))

    out = capsys.readouterr().out
    assert "[DEBUG] 소스코드 로딩: " in out
    assert "1번째 줄에서 정지" in out and "→ var a = 3;" in out
    assert "2번째 줄에서 정지" in out and "→ var b = a + 1;" in out
    assert "3번째 줄에서 정지" in out and "→ print b;" in out
    assert "4" in out.splitlines()
    assert "[DEBUG] 실행이 종료되었습니다." in out


def test_run_debug_mode_breakpoint_and_continue_skips_intermediate_lines(
    tmp_path, capsys, monkeypatch
):
    path = tmp_path / "program.cf"
    path.write_text("var a = 0;\nvar b = 1;\nvar c = 2;\nprint c;\n", encoding="utf-8")

    _feed_input(monkeypatch, ["break 3", "continue", "continue"])

    factory_shell.run_debug_mode(str(path))

    out = capsys.readouterr().out
    assert "1번째 줄에서 정지" in out and "→ var a = 0;" in out
    assert "3번째 줄에 breakpoint 설정" in out
    assert "3번째 줄에서 정지" in out and "→ var c = 2;" in out
    assert "2번째 줄에서 정지" not in out
    assert "2" in out.splitlines()


def test_run_debug_mode_next_skips_over_block_body(tmp_path, capsys, monkeypatch):
    path = tmp_path / "program.cf"
    path.write_text("var a = 0;\n{\n    a = 1;\n}\nprint a;\n", encoding="utf-8")

    _feed_input(monkeypatch, ["next", "next", "continue"])

    factory_shell.run_debug_mode(str(path))

    out = capsys.readouterr().out
    assert out.count("줄에서 정지") == 3
    assert "1" in out.splitlines()


def test_run_debug_mode_watch_prints_value_at_each_pause(tmp_path, capsys, monkeypatch):
    path = tmp_path / "program.cf"
    path.write_text("var a = 1;\nvar b = 2;\nprint a;\n", encoding="utf-8")

    _feed_input(monkeypatch, ["watch a", "step", "step", "continue"])

    factory_shell.run_debug_mode(str(path))

    out = capsys.readouterr().out
    assert "[WATCH] 'a' 감시 등록" in out
    assert "[WATCH] a = 1" in out


def test_run_debug_mode_inspect_prints_current_scope(tmp_path, capsys, monkeypatch):
    path = tmp_path / "program.cf"
    path.write_text("var a = 1;\nvar b = 2;\nprint b;\n", encoding="utf-8")

    _feed_input(monkeypatch, ["step", "inspect", "continue"])

    factory_shell.run_debug_mode(str(path))

    out = capsys.readouterr().out
    assert "[전역] a = 1 (Number)" in out


def test_run_debug_mode_reports_runtime_error_with_line_number(
    tmp_path, capsys, monkeypatch
):
    path = tmp_path / "program.cf"
    path.write_text("var arr = Array(2);\nprint arr[5];\n", encoding="utf-8")

    _feed_input(monkeypatch, ["continue"])

    with pytest.raises(SystemExit) as exc_info:
        factory_shell.run_debug_mode(str(path))

    assert exc_info.value.code == 1
    assert "[2번째줄] 배열 인덱스가 범위를 벗어났습니다." in capsys.readouterr().out


def test_run_debug_mode_exit_stops_without_running_remaining_statements(
    tmp_path, capsys, monkeypatch
):
    path = tmp_path / "program.cf"
    path.write_text("var a = 1;\nprint a;\n", encoding="utf-8")

    _feed_input(monkeypatch, ["exit"])

    factory_shell.run_debug_mode(str(path))  # 정상 종료(exit code 1로 죽지 않음)

    out = capsys.readouterr().out
    assert "디버그 세션을 종료합니다" in out
    assert "1" not in out.splitlines()  # print a;가 실행되지 않았어야 한다
    assert "[DEBUG] 실행이 종료되었습니다." not in out
