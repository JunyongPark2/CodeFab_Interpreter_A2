# test_prompt_shell.py — prompt_shell.py(REPL 진입점) 통합 테스트
#
# 실행: pytest tests/test_prompt_shell.py -v
#
# prompt_shell.run()은 CodeFabInterpreter 하나를 REPL 세션 내내 재사용하므로,
# 아래 테스트도 실제 REPL처럼 "같은 interpreter 인스턴스에 여러 줄을 순서대로 넣는다."

import pytest

from interpreter.codefab import CodeFabInterpreter
from prompt_shell import run


@pytest.fixture
def interpreter():
    return CodeFabInterpreter()


# ── 산술 / 연산자 우선순위 ─────────────────────────────────────────────

@pytest.mark.parametrize("source,expected", [
    ("print 1 + 2 * 3;", "7"),
    ("print (1 + 2) * 3;", "9"),
    ("print 10 - 4 - 3;", "3"),
    ("print 8 / 2 / 2;", "2"),
    ("print -3 + 2;", "-1"),
])
def test_arithmetic_and_precedence(interpreter, capsys, source, expected):
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == expected


# ── 비교 / 동등성 ──────────────────────────────────────────────────────

@pytest.mark.parametrize("source,expected", [
    ("print 1 < 2;", "true"),
    ("print 3 > 5;", "false"),
])
def test_comparison(interpreter, capsys, source, expected):
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == expected


# ── 문자열 연결 ────────────────────────────────────────────────────────

def test_string_concatenation(interpreter, capsys):
    run(interpreter, 'print "Hello, " + "CodeFab!";')
    assert capsys.readouterr().out.strip() == "Hello, CodeFab!"


# ── 숫자 출력 포맷 (정수는 .0 없이 출력) ────────────────────────────────

@pytest.mark.parametrize("source,expected", [
    ("print 5;", "5"),
    ("print 5.0;", "5"),
    ("print 3.14;", "3.14"),
])
def test_number_format(interpreter, capsys, source, expected):
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == expected


# ── boolean 리터럴 출력 ─────────────────────────────────────────────────

@pytest.mark.parametrize("source,expected", [
    ("print true;", "true"),
    ("print false;", "false"),
])
def test_boolean_literal(interpreter, capsys, source, expected):
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == expected


# ── 전체 스크립트를 한 세션(같은 interpreter)에서 순서대로 실행 ────────────

def test_full_script_line_by_line_matches_expected_output(interpreter, capsys):
    script = [
        ("print 1 + 2 * 3;", "7"),
        ("print (1 + 2) * 3;", "9"),
        ("print 10 - 4 - 3;", "3"),
        ("print 8 / 2 / 2;", "2"),
        ("print -3 + 2;", "-1"),
        ("print 1 < 2;", "true"),
        ("print 3 > 5;", "false"),
        ('print "Hello, " + "CodeFab!";', "Hello, CodeFab!"),
        ("print 5;", "5"),
        ("print 5.0;", "5"),
        ("print 3.14;", "3.14"),
        ("print true;", "true"),
        ("print false;", "false"),
    ]
    for source, expected in script:
        run(interpreter, source)
        assert capsys.readouterr().out.strip() == expected


# ── 변수 선언/재할당/블록 스코프/shadowing/중첩 스코프 ───────────────────
#
# 실제 REPL에서 "{ ... }"처럼 여러 줄에 걸친 블록을 한 줄씩 입력하면
# 아직 미완성 문장인 상태로 바로 파싱을 시도해 에러가 나기 때문에(연속 입력
# 미지원), 블록 하나는 "\n"으로 이어붙인 문자열 하나를 run()에 한 번에 넘겨서
# 마치 사용자가 블록 전체를 붙여넣은 것처럼 테스트한다. (블록이 아닌 단문은
# 한 줄씩 그대로 run()에 넘긴다.)

def test_declare_and_use(interpreter, capsys):
    run(interpreter, "var a = 10;")
    assert capsys.readouterr().out == ""

    run(interpreter, "var b = 20;")
    assert capsys.readouterr().out == ""

    run(interpreter, "print a + b;")
    assert capsys.readouterr().out.strip() == "30"


def test_reassignment(interpreter, capsys):
    run(interpreter, "var a = 10;")
    capsys.readouterr()

    run(interpreter, "a = a + 5;")
    assert capsys.readouterr().out == ""

    run(interpreter, "print a;")
    assert capsys.readouterr().out.strip() == "15"


def test_block_scope_and_shadowing(interpreter, capsys):
    run(interpreter, 'var x = "global";')
    assert capsys.readouterr().out == ""

    run(interpreter, '{\n  var x = "inner";\n  print x;\n}')
    assert capsys.readouterr().out.strip() == "inner"

    # 블록 밖은 영향받지 않는다.
    run(interpreter, "print x;")
    assert capsys.readouterr().out.strip() == "global"


def test_inner_block_can_mutate_outer_variable(interpreter, capsys):
    run(interpreter, "var count = 0;")
    assert capsys.readouterr().out == ""

    # 같은 이름 재선언이 아니라 바깥 변수를 직접 수정하는 것이므로 출력이 없다.
    run(interpreter, "{\n  count = count + 1;\n}")
    assert capsys.readouterr().out == ""

    run(interpreter, "print count;")
    assert capsys.readouterr().out.strip() == "1"


def test_nested_scope_resolution(interpreter, capsys):
    run(interpreter, 'var outer = "A";')
    assert capsys.readouterr().out == ""

    run(interpreter, '{\n  var inner = "B";\n  {\n    print outer + inner;\n  }\n}')
    assert capsys.readouterr().out.strip() == "AB"


def test_full_variable_and_scope_script(interpreter, capsys):
    # 위 다섯 개 테스트를 하나의 REPL 세션(같은 interpreter)에서 순서대로 실행한 통합 버전.
    script = [
        ("var a = 10;", ""),
        ("var b = 20;", ""),
        ("print a + b;", "30"),
        ("a = a + 5;", ""),
        ("print a;", "15"),
        ('var x = "global";', ""),
        ('{\n  var x = "inner";\n  print x;\n}', "inner"),
        ("print x;", "global"),
        ("var count = 0;", ""),
        ("{\n  count = count + 1;\n}", ""),
        ("print count;", "1"),
        ('var outer = "A";', ""),
        ('{\n  var inner = "B";\n  {\n    print outer + inner;\n  }\n}', "AB"),
    ]
    for source, expected in script:
        run(interpreter, source)
        assert capsys.readouterr().out.strip() == expected


# ── if / else / for ──────────────────────────────────────────────────
#
# 여기서도 여러 줄에 걸친 구문(중첩 if/else, for의 블록 바디)은 "\n"으로
# 이어붙인 문자열 하나를 run()에 한 번에 넘겨서, 사용자가 블록 전체를
# 붙여넣은 것처럼 테스트한다.

def test_if_without_else(interpreter, capsys):
    run(interpreter, 'if (true) print "bbq";')
    assert capsys.readouterr().out.strip() == "bbq"


def test_if_else(interpreter, capsys):
    run(interpreter, 'if (false) print "no"; else print "kfc";')
    assert capsys.readouterr().out.strip() == "kfc"


def test_else_binds_to_nearest_if(interpreter, capsys):
    # else는 가장 가까운 if(false)에 결합되어야 한다 → "kfc"가 아니라 "bbq".
    source = (
         'if (true)\n{\n  if (false) print "kfc";\n  else print "bbq";\n}'
    )
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == "bbq"


def test_for_loop_counts_up(interpreter, capsys):
    source = 'for (var j = 0; j < 3; j = j + 1) { print j; }'
    run(interpreter, source)
    assert capsys.readouterr().out.strip().splitlines() == ["0", "1", "2"]


def test_full_if_else_for_script(interpreter, capsys):
    # 위 네 시나리오를 한 세션(같은 interpreter)에서 순서대로 실행한 통합 버전.
    script = [
        ('if (true) print "bbq";', "bbq"),
        ('if (false) print "no"; else print "kfc";', "kfc"),
        (
            'if (true)\n{\n  if (false) print "kfc";\n  else print "bbq";\n}',
            "bbq",
        ),
        (
            'for (var j = 0; j < 3; j = j + 1) { print j; }',
            "0\n1\n2",
        ),
    ]
    for source, expected in script:
        run(interpreter, source)
        assert capsys.readouterr().out.strip() == expected
