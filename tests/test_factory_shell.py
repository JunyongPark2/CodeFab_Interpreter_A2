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


def test_run_file_mode_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        factory_shell.run_file_mode("program.cf")


def test_run_debug_mode_not_implemented_yet():
    with pytest.raises(NotImplementedError):
        factory_shell.run_debug_mode("program.cf")
