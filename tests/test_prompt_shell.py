import builtins

import pytest

from interpreter.codefab import CodeFabInterpreter
from interpreter.errors import (
    CheckError,
    CodeFabRuntimeError,
    ParseError,
    TokenizeError,
)
from prompt_shell import _needs_more_input, main, run


def _feed_lines(monkeypatch, lines):
    """input()을 모킹해서, 사용자가 lines를 한 줄씩 타이핑하는 것처럼 흉내낸다.
    lines가 다 소진되면 실제 input()의 EOF(Ctrl+D)와 동일하게 EOFError를 던진다.
    프롬프트 문자열(">> ", "... ")은 실제 input()과 달리 stdout에 찍히지 않으므로,
    capsys로 캡처되는 내용은 프로그램이 print()한 결과만 남는다.
    """
    it = iter(lines)

    def fake_input(prompt=""):
        try:
            return next(it)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr(builtins, "input", fake_input)


@pytest.fixture
def interpreter():
    return CodeFabInterpreter()


# ── 산술 / 연산자 우선순위 ─────────────────────────────────────────────


@pytest.mark.parametrize(
    "source,expected",
    [
        ("print 1 + 2 * 3;", "7"),
        ("print (1 + 2) * 3;", "9"),
        ("print 10 - 4 - 3;", "3"),
        ("print 8 / 2 / 2;", "2"),
        ("print -3 + 2;", "-1"),
    ],
)
def test_arithmetic_and_precedence(interpreter, capsys, source, expected):
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == expected


# ── 비교 / 동등성 ──────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source,expected",
    [
        ("print 1 < 2;", "true"),
        ("print 3 > 5;", "false"),
    ],
)
def test_comparison(interpreter, capsys, source, expected):
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == expected


# ── 문자열 연결 ────────────────────────────────────────────────────────


def test_string_concatenation(interpreter, capsys):
    run(interpreter, 'print "Hello, " + "CodeFab!";')
    assert capsys.readouterr().out.strip() == "Hello, CodeFab!"


# ── 숫자 출력 포맷 (정수는 .0 없이 출력) ────────────────────────────────


@pytest.mark.parametrize(
    "source,expected",
    [
        ("print 5;", "5"),
        ("print 5.0;", "5"),
        ("print 3.14;", "3.14"),
    ],
)
def test_number_format(interpreter, capsys, source, expected):
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == expected


# ── boolean 리터럴 출력 ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "source,expected",
    [
        ("print true;", "true"),
        ("print false;", "false"),
    ],
)
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


def test_repl_run_prints_import_error_without_traceback(interpreter, capsys):
    run(interpreter, 'import "missing_file_for_manual_check.txt" alias m;')

    out = capsys.readouterr().out
    assert "import 대상 파일이 없습니다" in out
    assert "Traceback" not in out


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
    source = 'if (true)\n{\n  if (false) print "kfc";\n  else print "bbq";\n}'
    run(interpreter, source)
    assert capsys.readouterr().out.strip() == "bbq"


def test_for_loop_counts_up(interpreter, capsys):
    source = "for (var j = 0; j < 3; j = j + 1) { print j; }"
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
            "for (var j = 0; j < 3; j = j + 1) { print j; }",
            "0\n1\n2",
        ),
    ]
    for source, expected in script:
        run(interpreter, source)
        assert capsys.readouterr().out.strip() == expected


# ── 에러 검출 (Tokenizer / Parser / Checker / Executor) ───────────────
#
# 각 케이스마다 두 가지를 검증한다.
#   1) CodeFabInterpreter.run(source)를 직접 호출하면 "정확한 예외 타입"이
#      그대로 raise되는지 (prompt_shell.run()은 예외를 잡아서 출력만 하므로,
#      타입 검증은 예외를 그대로 던지는 interpreter.run()으로 확인한다.)
#   2) 실제 REPL 진입점인 prompt_shell.run()으로 실행하면 예외가 밖으로
#      새지 않고, 대신 stdout에 정확한 에러 메시지가 출력되는지.

ERROR_CASES = [
    # (설명, source, 예외 타입, 기대 메시지)
    (
        "세미콜론 누락",
        "print 1 + 2",
        ParseError,
        "[1번째줄] ';' 가 필요합니다.",
    ),
    (
        "닫는 괄호 누락",
        "print (1 + 2;",
        ParseError,
        "[1번째줄] ')' 가 필요합니다.",
    ),
    (
        "잘못된 할당 대상",
        "a + b = 3;",
        ParseError,
        "[1번째줄] 대입 대상이 올바르지 않습니다.",
    ),
    (
        "표현식 자리에 잘못된 토큰",
        "print * 5;",
        ParseError,
        "[1번째줄] 표현식이 필요합니다.",
    ),
    (
        "초기화식에서 자기 참조",
        "{ var a = a; }",
        CheckError,
        "[1번째줄] 자신의 초기화식에서 지역변수를 읽을 수 없습니다.",
    ),
    (
        "같은 스코프 중복 선언",
        '{ var a = "hi"; var a = 3; }',
        CheckError,
        "[1번째줄] 변수 'a'이(가) 이미 이 스코프에 선언되어 있습니다.",
    ),
    (
        "미정의 변수 참조",
        "print notDefined;",
        CodeFabRuntimeError,
        "[1번째줄] 미정의된 변수 'notDefined'",
    ),
    (
        "+ 연산 타입 혼용",
        'print 1 + "HI";',
        CodeFabRuntimeError,
        "[1번째줄] 피연산자는 반드시 숫자 또는 문자열이어야 합니다.",
    ),
    (
        "단항 -에 비숫자 적용",
        'print -"FabCoding";',
        CodeFabRuntimeError,
        "[1번째줄] 피연산자는 반드시 숫자여야 합니다.",
    ),
    (
        "인식 불가 문자 (Tokenizer)",
        "print @;",
        TokenizeError,
        "[1번째줄] 인식할 수 없는 문자: '@'",
    ),
]


@pytest.mark.parametrize(
    "desc,source,error_cls,expected_msg",
    ERROR_CASES,
    ids=[desc for desc, *_ in ERROR_CASES],
)
def test_interpreter_run_raises_expected_exception_type_and_message(
    interpreter,
    desc,
    source,
    error_cls,
    expected_msg,
):
    with pytest.raises(error_cls) as exc_info:
        interpreter.run(source)
    assert str(exc_info.value) == expected_msg


@pytest.mark.parametrize(
    "desc,source,error_cls,expected_msg",
    ERROR_CASES,
    ids=[desc for desc, *_ in ERROR_CASES],
)
def test_prompt_shell_run_prints_error_message_without_raising(
    interpreter,
    capsys,
    desc,
    source,
    error_cls,
    expected_msg,
):
    run(interpreter, source)  # 예외가 여기서 새어나오면 테스트 자체가 실패한다.
    assert capsys.readouterr().out.strip() == expected_msg


def test_repl_recovers_after_error_and_keeps_previous_state(interpreter, capsys):
    # 한 줄에서 에러가 나도 REPL은 죽지 않고, 그 전에 선언한 변수도 그대로 유지된다.
    run(interpreter, "var a = 10;")
    assert capsys.readouterr().out == ""

    run(interpreter, "print notDefined;")
    assert capsys.readouterr().out.strip() == "[1번째줄] 미정의된 변수 'notDefined'"

    run(interpreter, "print a;")
    assert capsys.readouterr().out.strip() == "10"


# ── 여러 줄 연속 입력 (Python 셸의 '...' 이어받기) ──────────────────────
#
# _needs_more_input()은 tokenize+parse만 해보고 ParseError.incomplete로
# 판단하므로, 부작용(변수 선언/print 등) 없이 단위 테스트할 수 있다.


@pytest.mark.parametrize(
    "source",
    [
        "if (true",  # '(' 자체가 안 닫힘 (EOF)
        "print (1 + 2",  # 그루핑 '('가 안 닫힘 (EOF)
        "for (var i = 0; i < 5; i = i + 1) {",  # '{'는 헤더와 같은 줄, 안 닫힘
        "for (var i = 0; i < 5; i = i + 1) {\n  print i;",  # 안 닫힌 '{'
        "if (true) {",  # '{'만 열리고 안 닫힘
        "if (true) {\n  print 1;\n} else {",  # else 블록의 '{'가 안 닫힘
        "{",  # 블록 시작만 됨
    ],
)
def test_needs_more_input_true_when_closing_bracket_missing_at_eof(source):
    assert _needs_more_input(source) is True


@pytest.mark.parametrize(
    "source",
    [
        # ')' 자리에 EOF가 아니라 다른 토큰(';')이 이미 와버린 경우 — 몇 줄을
        # 더 받아도 절대 고쳐지지 않는 진짜 에러이므로 기다리면 안 된다.
        # (괄호 개수만 세면 "안 닫혔다"고 오판해서 영원히 기다리게 되는 버그였음)
        "print (1 + 2;",
        "if (true; { print 1; }",
    ],
)
def test_needs_more_input_false_when_wrong_token_appears_instead_of_closing_bracket(
    source,
):
    assert _needs_more_input(source) is False


@pytest.mark.parametrize(
    "source",
    [
        # 괄호는 이미 다 닫혔지만, if/for/else의 본문(statement) 자리에
        # 아무것도 없는 경우 — Python이 "if x:" 뒤에 들여쓰기 블록을 기다리는
        # 것과 대응되는, 우리 문법에서 유일하게 구두점 없이 Stmt가 그대로
        # 요구되는 자리라서 기다려야 한다.
        "for (var i = 0; i < 5; i = i + 1)",  # '{' 자체가 아직 없음
        "if (true)",  # then_branch가 없음
        "if (true) {\n  print 1;\n}\nelse",  # else의 문장이 없음
    ],
)
def test_needs_more_input_true_for_missing_body_statement(source):
    assert _needs_more_input(source) is True


@pytest.mark.parametrize(
    "source",
    [
        "print 1 + 2;",
        "var a = 1;",
        "for (var i = 0; i < 5; i = i + 1) {\n  print i;\n}",
        "if (true) {\n  print 1;\n} else {\n  print 2;\n}",
        # 괄호/중괄호가 다 맞고 "본문 자리"도 아닌데 뭔가 빠졌으면
        # (연산자 우변, 초기화식 등) Python 셸처럼 더 기다리지 않고
        # 바로 에러를 보여준다.
        "print 1 +",  # 이항 연산자 우변이 없음 → 즉시 에러
        "var a =",  # 초기화식이 없음 → 즉시 에러
        "print 1 +\n2;",  # 이어붙이면 완전한 문장이 된다.
    ],
)
def test_needs_more_input_false_when_already_complete_or_real_error(source):
    assert _needs_more_input(source) is False


@pytest.mark.parametrize(
    "source",
    [
        "print * 5;",  # 표현식 자리에 잘못된 토큰
        "print @;",  # Tokenizer 레벨 에러
    ],
)
def test_needs_more_input_false_for_real_errors(source):
    # 더 받아도 고쳐지지 않는 "진짜" 에러이므로 기다리지 않고
    # 바로 실행 단계로 넘겨서 에러를 보여줘야 한다.
    assert _needs_more_input(source) is False


def test_main_accumulates_multiline_for_loop_before_executing(monkeypatch, capsys):
    _feed_lines(
        monkeypatch,
        [
            "for (var i = 0; i < 5; i = i + 1) {",  # '{'는 헤더와 같은 줄에 둔다
            "  print i;",
            "}",
        ],
    )
    main()
    assert capsys.readouterr().out.strip() == "0\n1\n2\n3\n4"


def test_main_accumulates_multiline_if_else_before_executing(monkeypatch, capsys):
    # else 없는 '{ }' if는 else가 더 붙을 수 있으므로, 파이썬 셸처럼 빈 줄로
    # 확정해줘야 실행된다.
    _feed_lines(
        monkeypatch,
        [
            "if (true) {",  # '{'는 헤더와 같은 줄에 둔다
            '  print "bbq";',
            "}",
            "",  # 빈 줄 — else를 더 기다리지 않고 여기서 확정하고 실행
        ],
    )
    main()
    assert capsys.readouterr().out.strip() == "bbq"


def test_main_waits_for_blank_line_before_running_braced_if_without_else(
    monkeypatch, capsys
):
    # '{ }' if가 끝난 직후에는 else가 이어붙을 수 있으므로 곧바로 실행하지
    # 않고 '...' 프롬프트로 대기하다가, else가 오면 이어붙이고 없으면 빈
    # 줄에서 실행한다.
    _feed_lines(
        monkeypatch,
        [
            "if (true) {",
            '  print "bbq";',
            "}",
            "else {",
            '  print "kfc";',
            "}",
            "",
        ],
    )
    main()
    assert capsys.readouterr().out.strip() == "bbq"


def test_main_waits_for_body_when_brace_is_on_its_own_line(monkeypatch, capsys):
    # '{'가 for 헤더와 다른 줄에 있어도, 본문(statement) 자리가 비어있으면
    # 여전히 기다렸다가 실행해야 한다.
    _feed_lines(
        monkeypatch,
        ["for (var i = 0; i < 3; i = i + 1)", "{", "  print i;", "}"],
    )
    main()
    assert capsys.readouterr().out.strip() == "0\n1\n2"


def test_main_waits_for_bodyless_if_across_lines_without_braces(monkeypatch, capsys):
    # '{' 없이 단문 body를 다음 줄에 쓰는 경우도 기다렸다가 실행해야 한다.
    _feed_lines(
        monkeypatch,
        [
            "if (true)",
            "print 1;",
        ],
    )
    main()
    assert capsys.readouterr().out.strip() == "1"


def test_main_shows_real_syntax_error_immediately_without_waiting(monkeypatch, capsys):
    _feed_lines(
        monkeypatch,
        [
            "print * 5;",
            "print 1;",
        ],
    )
    main()
    out = capsys.readouterr().out
    assert out.strip() == "[1번째줄] 표현식이 필요합니다.\n1"


def test_main_executes_single_line_statements_immediately(monkeypatch, capsys):
    _feed_lines(
        monkeypatch,
        [
            "var a = 10;",
            "print a;",
        ],
    )
    main()
    assert capsys.readouterr().out.strip() == "10"


def test_main_exits_on_exit_command_without_running_later_lines(monkeypatch, capsys):
    _feed_lines(
        monkeypatch,
        [
            "print 1;",
            "exit()",
            "print 2;",
        ],
    )
    main()
    assert capsys.readouterr().out == "1\n"


def test_main_preserves_variables_across_multiline_and_single_line_input(
    monkeypatch, capsys
):
    _feed_lines(
        monkeypatch,
        [
            "var total = 0;",
            "for (var i = 0; i < 3; i = i + 1) {",  # '{'는 헤더와 같은 줄에 둔다
            "  total = total + i;",
            "}",
            "print total;",
        ],
    )
    main()
    assert capsys.readouterr().out.strip() == "3"
