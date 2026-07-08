import pytest

from interpreter.codefab import CodeFabInterpreter
from interpreter.errors import CheckError, LangRuntimeError, ParseError, TokenizeError


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
    interp.run(
        "for (var i = 0; i < 2; i = i + 1) { for (var j = 0; j < 2; j = j + 1) { print i + j; } }"
    )
    assert capsys.readouterr().out == "0\n1\n1\n2\n"


def test_nested_for_loop_vars_do_not_leak_into_global_scope(interp, capsys):
    interp.run(
        "for (var i = 0; i < 2; i = i + 1) { for (var j = 0; j < 2; j = j + 1) { print i + j; } }"
    )
    capsys.readouterr()
    interp.run("var i = 10; var j = 20; print i + j;")
    assert capsys.readouterr().out == "30\n"


def test_nested_for_loop_same_var_shadowing(interp, capsys):
    interp.run(
        "for (var i = 0; i < 2; i = i + 1) { for (var i = 10; i < 12; i = i + 1) { print i; } }"
    )
    assert capsys.readouterr().out == "10\n11\n10\n11\n"


# ── Function ──────────────────────────────────────────────────────────────────


def test_function_declaration_and_call(interp, capsys):
    interp.run("Func greet() { print \"hi\"; } greet();")
    assert capsys.readouterr().out == "hi\n"


def test_function_with_params_and_return(interp, capsys):
    interp.run("Func add(a, b) { return a + b; } print add(3, 4);")
    assert capsys.readouterr().out == "7\n"


def test_function_return_nil(interp, capsys):
    interp.run("Func noop() { return; } print noop();")
    assert capsys.readouterr().out == "nil\n"


def test_function_no_return_is_nil(interp, capsys):
    interp.run("Func noop() { } print noop();")
    assert capsys.readouterr().out == "nil\n"


def test_function_return_value_in_variable(interp, capsys):
    interp.run("Func double(x) { return x * 2; } var r = double(5); print r;")
    assert capsys.readouterr().out == "10\n"


def test_recursive_factorial(interp, capsys):
    source = """\
Func fact(n) {
  if (n < 2) return 1;
  return n * fact(n - 1);
}
print fact(5);
"""
    interp.run(source)
    assert capsys.readouterr().out == "120\n"


def test_function_non_callable_raises(interp):
    with pytest.raises(LangRuntimeError):
        interp.run("var x = 1; x();")


def test_function_arity_mismatch_raises(interp):
    with pytest.raises(LangRuntimeError):
        interp.run("Func add(a, b) { return a + b; } add(1);")


def test_return_outside_function_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("return 5;")


def test_duplicate_param_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("Func bad(x, x) { return x; }")


# ── Class — 기본 기능 ──────────────────────────────────────────────────────────


def test_empty_class_instance(interp, capsys):
    interp.run("Class Robot { } var r = Robot(); print r;")
    assert capsys.readouterr().out == "<Robot instance>\n"


def test_field_write_and_read(interp, capsys):
    interp.run("Class Robot { } var r = Robot(); r.speed = 10; print r.speed;")
    assert capsys.readouterr().out == "10\n"


def test_field_update(interp, capsys):
    interp.run(
        "Class Robot { } var r = Robot(); r.speed = 5; r.speed = r.speed + 3; print r.speed;"
    )
    assert capsys.readouterr().out == "8\n"


def test_nonexistent_field_read_raises(interp):
    with pytest.raises(LangRuntimeError):
        interp.run("Class Robot { } var r = Robot(); print r.speed;")


def test_method_with_this(interp, capsys):
    source = """\
Class Robot {
  Func setSpeed(s) {
    This.speed = s;
  }
  Func getSpeed() {
    return This.speed;
  }
}
var r = Robot();
r.setSpeed(42);
print r.getSpeed();
"""
    interp.run(source)
    assert capsys.readouterr().out == "42\n"


def test_method_calls_another_method(interp, capsys):
    source = """\
Class Counter {
  Func init() {
    This.count = 0;
  }
  Func increment() {
    This.count = This.count + 1;
  }
  Func getCount() {
    return This.count;
  }
}
var c = Counter();
c.increment();
c.increment();
print c.getCount();
"""
    interp.run(source)
    assert capsys.readouterr().out == "2\n"


def test_init_constructor_with_args(interp, capsys):
    source = """\
Class Robot {
  Func init(name, speed) {
    This.name = name;
    This.speed = speed;
  }
}
var r = Robot("AndOr", 10);
print r.name;
print r.speed;
"""
    interp.run(source)
    assert capsys.readouterr().out == "AndOr\n10\n"


def test_init_returns_instance(interp, capsys):
    interp.run("Class Robot { Func init() { This.x = 1; } } var r = Robot(); print r.x;")
    assert capsys.readouterr().out == "1\n"


def test_this_outside_class_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("print This.x;")


def test_init_return_value_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("Class Bad { Func init() { return 1; } }")


def test_non_instance_field_access_raises(interp):
    with pytest.raises(LangRuntimeError):
        interp.run("var x = 42; print x.speed;")


# ── Class — 상속 / Super / instanceof ────────────────────────────────────────


def test_child_inherits_parent_method(interp, capsys):
    source = """\
Class Animal {
  Func speak() { print "..."; }
}
Class Dog : Animal { }
var d = Dog();
d.speak();
"""
    interp.run(source)
    assert capsys.readouterr().out == "...\n"


def test_child_overrides_parent_method(interp, capsys):
    source = """\
Class Animal {
  Func speak() { print "..."; }
}
Class Dog : Animal {
  Func speak() { print "woof"; }
}
var d = Dog();
d.speak();
"""
    interp.run(source)
    assert capsys.readouterr().out == "woof\n"


def test_super_calls_parent_method(interp, capsys):
    source = """\
Class Robot {
  Func greet() { print "Robot"; }
}
Class SpeedRobot : Robot {
  Func greet() {
    Super.greet();
    print "SpeedRobot";
  }
}
var r = SpeedRobot();
r.greet();
"""
    interp.run(source)
    assert capsys.readouterr().out == "Robot\nSpeedRobot\n"


def test_super_with_this_fields(interp, capsys):
    source = """\
Class Robot {
  Func init(name) {
    This.name = name;
  }
  Func greet() {
    print This.name;
  }
}
Class SpeedRobot : Robot {
  Func init(name, speed) {
    This.name = name;
    This.speed = speed;
  }
  Func greet() {
    Super.greet();
    print This.speed;
  }
}
var r = SpeedRobot("Bolt", 100);
r.greet();
"""
    interp.run(source)
    assert capsys.readouterr().out == "Bolt\n100\n"


def test_instanceof_own_class_is_true(interp, capsys):
    interp.run("Class Robot { } var r = Robot(); print r instanceof Robot;")
    assert capsys.readouterr().out == "true\n"


def test_instanceof_parent_class_is_true(interp, capsys):
    source = """\
Class Animal { }
Class Dog : Animal { }
var d = Dog();
print d instanceof Dog;
print d instanceof Animal;
"""
    interp.run(source)
    assert capsys.readouterr().out == "true\ntrue\n"


def test_instanceof_unrelated_class_is_false(interp, capsys):
    source = """\
Class Cat { }
Class Dog { }
var d = Dog();
print d instanceof Cat;
"""
    interp.run(source)
    assert capsys.readouterr().out == "false\n"


def test_instanceof_non_instance_is_false(interp, capsys):
    interp.run("Class Robot { } print 42 instanceof Robot;")
    assert capsys.readouterr().out == "false\n"


def test_self_inheritance_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("Class A : A { }")


def test_non_class_inheritance_raises_runtime_error(interp):
    with pytest.raises(LangRuntimeError):
        interp.run("var A = 1; Class B : A { }")


def test_super_outside_class_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("Super.greet();")


def test_super_without_parent_raises_check_error(interp):
    with pytest.raises(CheckError):
        interp.run("Class A { Func greet() { Super.greet(); } }")


def test_super_missing_method_raises_runtime_error(interp):
    with pytest.raises(LangRuntimeError):
        source = """\
Class A { }
Class B : A {
  Func test() { Super.nope(); }
}
var b = B();
b.test();
"""
        interp.run(source)
