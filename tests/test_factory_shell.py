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


def test_run_debug_mode_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        factory_shell.run_debug_mode("program.cf")


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
