import pytest

from interpreter.assembler import Assembler
from interpreter.ast_nodes import (
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ClassDeclStmt,
    ExpressionStmt,
    ForStmt,
    FuncDeclStmt,
    GetExpr,
    GroupingExpr,
    IfStmt,
    InstanceOfExpr,
    LiteralExpr,
    PrintStmt,
    ReturnStmt,
    SetExpr,
    ThisExpr,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from interpreter.errors import ParseError, TokenizeError
from interpreter.parser import Parser
from interpreter.tokenizer import Tokenizer
from interpreter.tokens import TokenType

# ─────────────────────────────────────────────────────────
# 헬퍼 — Tokenizer/Parser 클래스를 주입해 Assembler를 만든다
# ─────────────────────────────────────────────────────────


def assemble(source: str) -> list:
    return Assembler(Tokenizer, Parser).assemble(source)


def assemble_print(source: str):
    """`print <expr>;` 한 줄을 assemble해서 print 안의 표현식(Expr)만 꺼내준다."""
    stmts = assemble(source)
    assert len(stmts) == 1
    assert isinstance(stmts[0], PrintStmt)
    return stmts[0].expression


# ─────────────────────────────────────────────────────────
# Assembler 생성 자체에 대한 테스트 — 클래스 주입 방식 확인
# ─────────────────────────────────────────────────────────


def test_assembler_reuses_injected_tokenizer_and_parser_classes():
    # 생성 시 넘긴 Tokenizer/Parser 클래스 하나로 여러 번 assemble() 할 수 있어야 한다.
    # (매 assemble() 호출마다 내부적으로 새 Tokenizer(text)/Parser(tokens) 인스턴스를 만든다.)
    assembler = Assembler(Tokenizer, Parser)

    first = assembler.assemble("print 1;")
    second = assembler.assemble("print 2;")

    assert isinstance(first[0], PrintStmt)
    assert first[0].expression == LiteralExpr(1.0)
    assert isinstance(second[0], PrintStmt)
    assert second[0].expression == LiteralExpr(2.0)


# ─────────────────────────────────────────────────────────
# 산술 / 연산자 우선순위
# ─────────────────────────────────────────────────────────


def test_multiplication_precedes_addition():
    # print 1 + 2 * 3;
    expr = assemble_print("print 1 + 2 * 3;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS  # 루트는 +
    assert expr.left == LiteralExpr(1.0)

    assert isinstance(expr.right, BinaryExpr)  # 오른쪽은 2 * 3
    assert expr.right.operator.type == TokenType.STAR
    assert expr.right.left == LiteralExpr(2.0)
    assert expr.right.right == LiteralExpr(3.0)


def test_parentheses_override_precedence():
    # print (1 + 2) * 3;
    expr = assemble_print("print (1 + 2) * 3;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.STAR  # 루트는 *
    assert expr.right == LiteralExpr(3.0)

    assert isinstance(expr.left, GroupingExpr)  # 왼쪽은 괄호 묶음
    inner = expr.left.expression
    assert isinstance(inner, BinaryExpr)
    assert inner.operator.type == TokenType.PLUS
    assert inner.left == LiteralExpr(1.0)
    assert inner.right == LiteralExpr(2.0)


def test_subtraction_is_left_associative():
    # print 10 - 4 - 3;
    expr = assemble_print("print 10 - 4 - 3;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.MINUS
    assert expr.right == LiteralExpr(3.0)

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 10 - 4
    assert expr.left.operator.type == TokenType.MINUS
    assert expr.left.left == LiteralExpr(10.0)
    assert expr.left.right == LiteralExpr(4.0)


def test_division_is_left_associative():
    # print 8 / 2 / 2;
    expr = assemble_print("print 8 / 2 / 2;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.SLASH
    assert expr.right == LiteralExpr(2.0)

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 8 / 2
    assert expr.left.operator.type == TokenType.SLASH
    assert expr.left.left == LiteralExpr(8.0)
    assert expr.left.right == LiteralExpr(2.0)


def test_unary_minus_precedes_addition():
    # print -3 + 2;
    expr = assemble_print("print -3 + 2;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS  # 루트는 +
    assert expr.right == LiteralExpr(2.0)

    assert isinstance(expr.left, UnaryExpr)  # 왼쪽은 -3 (단항)
    assert expr.left.operator.type == TokenType.MINUS
    assert expr.left.right == LiteralExpr(3.0)


# ─────────────────────────────────────────────────────────
# 비교 / 문자열 연결 / boolean 리터럴
# ─────────────────────────────────────────────────────────


def test_less_than_operator():
    # print 1 < 2;
    expr = assemble_print("print 1 < 2;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.LESS
    assert expr.left == LiteralExpr(1.0)
    assert expr.right == LiteralExpr(2.0)


def test_greater_than_operator():
    # print 3 > 5;
    expr = assemble_print("print 3 > 5;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.GREATER
    assert expr.left == LiteralExpr(3.0)
    assert expr.right == LiteralExpr(5.0)


def test_string_concatenation():
    # print "Hello, " + "CodeFab!";
    expr = assemble_print('print "Hello, " + "CodeFab!";')

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS
    assert expr.left == LiteralExpr("Hello, ")
    assert expr.right == LiteralExpr("CodeFab!")


def test_boolean_true_literal():
    # print true;
    assert assemble_print("print true;") == LiteralExpr(True)


def test_boolean_false_literal():
    # print false;
    assert assemble_print("print false;") == LiteralExpr(False)


# ─────────────────────────────────────────────────────────
# 변수 선언 / 재할당 / 블록 스코프 / 섀도잉
# ─────────────────────────────────────────────────────────


def test_var_declaration():
    # var a = 10;
    stmts = assemble("var a = 10;")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, VarDeclStmt)
    assert stmt.name.origin == "a"
    assert stmt.initializer == LiteralExpr(10.0)


def test_variable_reference_after_declaration():
    # var a = 10; var b = 20; print a + b;   // expect: 30
    stmts = assemble(
        "var a = 10;\n" "var b = 20;\n" "print a + b;            // expect: 30\n"
    )

    assert len(stmts) == 3
    print_stmt = stmts[2]
    assert isinstance(print_stmt, PrintStmt)
    expr = print_stmt.expression
    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS
    assert isinstance(expr.left, VariableExpr)
    assert expr.left.name.origin == "a"
    assert isinstance(expr.right, VariableExpr)
    assert expr.right.name.origin == "b"


def test_reassignment():
    # a = a + 5;
    stmts = assemble("a = a + 5;")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ExpressionStmt)
    expr = stmt.expression
    assert isinstance(expr, AssignExpr)
    assert expr.name.origin == "a"
    rhs = expr.value
    assert isinstance(rhs, BinaryExpr)
    assert rhs.operator.type == TokenType.PLUS
    assert isinstance(rhs.left, VariableExpr)
    assert rhs.left.name.origin == "a"
    assert rhs.right == LiteralExpr(5.0)


def test_block_scope_and_shadowing():
    # var x = "global";
    # { var x = "inner"; print x; }   // expect: inner
    # print x;                        // expect: global
    stmts = assemble(
        'var x = "global";\n'
        "{\n"
        '  var x = "inner";\n'
        "  print x;              // expect: inner\n"
        "}\n"
        "print x;                // expect: global\n"
    )

    assert len(stmts) == 3
    outer_decl = stmts[0]
    assert isinstance(outer_decl, VarDeclStmt)
    assert outer_decl.name.origin == "x"
    assert outer_decl.initializer == LiteralExpr("global")

    block = stmts[1]
    assert isinstance(block, BlockStmt)
    assert len(block.statements) == 2
    inner_decl = block.statements[0]
    assert isinstance(inner_decl, VarDeclStmt)
    assert inner_decl.name.origin == "x"
    assert inner_decl.initializer == LiteralExpr("inner")
    inner_print = block.statements[1]
    assert isinstance(inner_print, PrintStmt)
    assert isinstance(inner_print.expression, VariableExpr)
    assert inner_print.expression.name.origin == "x"

    outer_print = stmts[2]
    assert isinstance(outer_print, PrintStmt)
    assert isinstance(outer_print.expression, VariableExpr)
    assert outer_print.expression.name.origin == "x"


def test_outer_variable_mutation_inside_block():
    # var count = 0;
    # { count = count + 1; }
    # print count;            // expect: 1
    stmts = assemble(
        "var count = 0;\n"
        "{\n"
        "  count = count + 1;    // 같은 이름 재선언이 아니라 바깥 변수 수정\n"
        "}\n"
        "print count;            // expect: 1\n"
    )

    assert len(stmts) == 3
    assert isinstance(stmts[0], VarDeclStmt)

    block = stmts[1]
    assert isinstance(block, BlockStmt)
    assert len(block.statements) == 1
    assign_stmt = block.statements[0]
    assert isinstance(assign_stmt, ExpressionStmt)
    assign = assign_stmt.expression
    assert isinstance(assign, AssignExpr)
    assert assign.name.origin == "count"
    assert isinstance(assign.value, BinaryExpr)

    assert isinstance(stmts[2], PrintStmt)


def test_nested_scope():
    # var outer = "A";
    # { var inner = "B"; { print outer + inner; } }   // expect: AB
    stmts = assemble(
        'var outer = "A";\n'
        "{\n"
        '  var inner = "B";\n'
        "  {\n"
        "    print outer + inner;  // expect: AB\n"
        "  }\n"
        "}\n"
    )

    assert len(stmts) == 2
    assert isinstance(stmts[0], VarDeclStmt)
    assert stmts[0].name.origin == "outer"

    outer_block = stmts[1]
    assert isinstance(outer_block, BlockStmt)
    assert len(outer_block.statements) == 2

    inner_decl = outer_block.statements[0]
    assert isinstance(inner_decl, VarDeclStmt)
    assert inner_decl.name.origin == "inner"

    inner_block = outer_block.statements[1]
    assert isinstance(inner_block, BlockStmt)
    assert len(inner_block.statements) == 1

    print_stmt = inner_block.statements[0]
    assert isinstance(print_stmt, PrintStmt)
    expr = print_stmt.expression
    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS
    assert isinstance(expr.left, VariableExpr)
    assert expr.left.name.origin == "outer"
    assert isinstance(expr.right, VariableExpr)
    assert expr.right.name.origin == "inner"


# ─────────────────────────────────────────────────────────
# 제어 흐름 — if / else / for
# ─────────────────────────────────────────────────────────


def test_if_true_simple():
    # if (true) print "bbq";
    stmts = assemble('if (true) print "bbq";')

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, IfStmt)
    assert stmt.condition == LiteralExpr(True)
    assert isinstance(stmt.then_branch, PrintStmt)
    assert stmt.then_branch.expression == LiteralExpr("bbq")
    assert stmt.else_branch is None


def test_if_else():
    # if (false) print "no"; else print "kfc";
    stmts = assemble('if (false) print "no"; else print "kfc";')

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, IfStmt)
    assert stmt.condition == LiteralExpr(False)
    assert isinstance(stmt.then_branch, PrintStmt)
    assert stmt.then_branch.expression == LiteralExpr("no")
    assert isinstance(stmt.else_branch, PrintStmt)
    assert stmt.else_branch.expression == LiteralExpr("kfc")


def test_dangling_else_binds_to_nearest_if():
    # if (true) if (false) print "kfc"; else print "bbq";
    #
    # else 는 바깥 if 가 아니라 가장 가까운 if(false) 에 붙어야 한다.
    stmts = assemble('if (true) if (false) print "kfc"; else print "bbq";')

    assert len(stmts) == 1
    outer = stmts[0]
    assert isinstance(outer, IfStmt)
    assert outer.condition == LiteralExpr(True)
    assert outer.else_branch is None  # 바깥 if 에는 else 없음

    inner = outer.then_branch
    assert isinstance(inner, IfStmt)
    assert inner.condition == LiteralExpr(False)
    assert isinstance(inner.then_branch, PrintStmt)
    assert inner.then_branch.expression == LiteralExpr("kfc")
    assert isinstance(inner.else_branch, PrintStmt)
    assert inner.else_branch.expression == LiteralExpr("bbq")


def test_for_loop():
    # for (var j = 0; j < 3; j = j + 1) { print j; }
    stmts = assemble("for (var j = 0; j < 3; j = j + 1) { print j; }")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ForStmt)

    # initializer: var j = 0
    assert isinstance(stmt.initializer, VarDeclStmt)
    assert stmt.initializer.name.origin == "j"
    assert stmt.initializer.initializer == LiteralExpr(0.0)

    # condition: j < 3
    cond = stmt.condition
    assert isinstance(cond, BinaryExpr)
    assert cond.operator.type == TokenType.LESS
    assert isinstance(cond.left, VariableExpr)
    assert cond.left.name.origin == "j"
    assert cond.right == LiteralExpr(3.0)

    # increment: j = j + 1
    inc = stmt.increment
    assert isinstance(inc, AssignExpr)
    assert inc.name.origin == "j"
    rhs = inc.value
    assert isinstance(rhs, BinaryExpr)
    assert rhs.operator.type == TokenType.PLUS
    assert isinstance(rhs.left, VariableExpr)
    assert rhs.left.name.origin == "j"
    assert rhs.right == LiteralExpr(1.0)

    # body: { print j; }
    assert isinstance(stmt.body, BlockStmt)
    assert len(stmt.body.statements) == 1
    print_stmt = stmt.body.statements[0]
    assert isinstance(print_stmt, PrintStmt)
    assert isinstance(print_stmt.expression, VariableExpr)
    assert print_stmt.expression.name.origin == "j"


# ─────────────────────────────────────────────────────────
# 전체 스크립트 통합 — 주석 / 여러 문장 / 제어 흐름이 섞인 실제 소스
# ─────────────────────────────────────────────────────────


class TestFullScriptIntegration:
    def test_declaration_reassignment_block_scope_full_script(self):
        source = """\
// --- 선언 & 사용 ---
var a = 10;
var b = 20;
print a + b;            // expect: 30

// --- 재할당 ---
a = a + 5;
print a;                // expect: 15
"""
        stmts = assemble(source)

        assert len(stmts) == 5
        assert isinstance(stmts[0], VarDeclStmt) and stmts[0].name.origin == "a"
        assert isinstance(stmts[1], VarDeclStmt) and stmts[1].name.origin == "b"
        assert isinstance(stmts[2], PrintStmt)
        assert isinstance(stmts[3], ExpressionStmt)
        assert isinstance(stmts[3].expression, AssignExpr)
        assert isinstance(stmts[4], PrintStmt)

    def test_control_flow_full_script(self):
        source = """\
if (true) print "bbq";

if (false) print "no"; else print "kfc";

for (var j = 0; j < 3; j = j + 1) { print j; }
"""
        stmts = assemble(source)

        assert len(stmts) == 3
        assert isinstance(stmts[0], IfStmt)
        assert stmts[0].else_branch is None
        assert isinstance(stmts[1], IfStmt)
        assert stmts[1].else_branch is not None
        assert isinstance(stmts[2], ForStmt)

    def test_empty_source_returns_empty_statement_list(self):
        assert assemble("") == []


# ─────────────────────────────────────────────────────────
# Function — 선언 / 호출 / return
# ─────────────────────────────────────────────────────────


def test_function_declaration_no_params():
    # Func greet() { print "hi"; }
    stmts = assemble('Func greet() { print "hi"; }')

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, FuncDeclStmt)
    assert stmt.name.origin == "greet"
    assert stmt.params == []
    assert len(stmt.body) == 1
    assert isinstance(stmt.body[0], PrintStmt)
    assert stmt.body[0].expression == LiteralExpr("hi")


def test_function_declaration_with_params():
    # Func add(a, b) { return a + b; }
    stmts = assemble("Func add(a, b) { return a + b; }")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, FuncDeclStmt)
    assert stmt.name.origin == "add"
    assert [p.origin for p in stmt.params] == ["a", "b"]

    assert len(stmt.body) == 1
    ret = stmt.body[0]
    assert isinstance(ret, ReturnStmt)
    assert isinstance(ret.value, BinaryExpr)
    assert ret.value.operator.type == TokenType.PLUS
    assert isinstance(ret.value.left, VariableExpr)
    assert ret.value.left.name.origin == "a"
    assert isinstance(ret.value.right, VariableExpr)
    assert ret.value.right.name.origin == "b"


def test_function_declaration_single_param():
    # Func square(x) { return x * x; }
    stmts = assemble("Func square(x) { return x * x; }")

    stmt = stmts[0]
    assert isinstance(stmt, FuncDeclStmt)
    assert [p.origin for p in stmt.params] == ["x"]


def test_return_without_value():
    # Func noop() { return; }
    stmts = assemble("Func noop() { return; }")

    ret = stmts[0].body[0]
    assert isinstance(ret, ReturnStmt)
    assert ret.value is None


def test_function_call_no_args():
    # add();
    stmts = assemble("add();")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ExpressionStmt)
    call = stmt.expression
    assert isinstance(call, CallExpr)
    assert isinstance(call.callee, VariableExpr)
    assert call.callee.name.origin == "add"
    assert call.arguments == []


def test_function_call_with_args():
    # add(1, 2);
    stmts = assemble("add(1, 2);")

    call = stmts[0].expression
    assert isinstance(call, CallExpr)
    assert call.callee.name.origin == "add"
    assert call.arguments == [LiteralExpr(1.0), LiteralExpr(2.0)]


def test_function_call_inside_print():
    # print add(1, 2);
    expr = assemble_print("print add(1, 2);")

    assert isinstance(expr, CallExpr)
    assert expr.callee.name.origin == "add"
    assert expr.arguments == [LiteralExpr(1.0), LiteralExpr(2.0)]


def test_nested_function_call_as_argument():
    # add(add(1, 2), 3);
    stmts = assemble("add(add(1, 2), 3);")

    outer = stmts[0].expression
    assert isinstance(outer, CallExpr)
    assert outer.callee.name.origin == "add"
    assert len(outer.arguments) == 2

    inner = outer.arguments[0]
    assert isinstance(inner, CallExpr)
    assert inner.callee.name.origin == "add"
    assert inner.arguments == [LiteralExpr(1.0), LiteralExpr(2.0)]

    assert outer.arguments[1] == LiteralExpr(3.0)


def test_recursive_function_body_can_reference_itself():
    # Func fact(n) {
    #   if (n < 2) return 1;
    #   return n * fact(n - 1);
    # }
    source = (
        "Func fact(n) {\n"
        "  if (n < 2) return 1;\n"
        "  return n * fact(n - 1);\n"
        "}\n"
    )
    stmts = assemble(source)

    stmt = stmts[0]
    assert isinstance(stmt, FuncDeclStmt)
    assert stmt.name.origin == "fact"
    assert [p.origin for p in stmt.params] == ["n"]
    assert len(stmt.body) == 2

    assert isinstance(stmt.body[0], IfStmt)

    second_return = stmt.body[1]
    assert isinstance(second_return, ReturnStmt)
    mult = second_return.value
    assert isinstance(mult, BinaryExpr)
    assert mult.operator.type == TokenType.STAR

    recursive_call = mult.right
    assert isinstance(recursive_call, CallExpr)
    assert recursive_call.callee.name.origin == "fact"
    assert isinstance(recursive_call.arguments[0], BinaryExpr)


def test_return_outside_function_parses_without_error():
    # return의 함수 외부 사용 금지는 Checker의 정적 검사 몫이므로,
    # Parser/Assembler 단계에서는 문법적으로 허용되어야 한다.
    stmts = assemble("return 5;")

    assert len(stmts) == 1
    assert isinstance(stmts[0], ReturnStmt)
    assert stmts[0].value == LiteralExpr(5.0)


def test_function_declaration_and_call_full_script():
    source = """\
Func add(a, b) {
  return a + b;
}

print add(1, 2);            // expect: 3
"""
    stmts = assemble(source)

    assert len(stmts) == 2
    assert isinstance(stmts[0], FuncDeclStmt)
    assert stmts[0].name.origin == "add"

    assert isinstance(stmts[1], PrintStmt)
    call = stmts[1].expression
    assert isinstance(call, CallExpr)
    assert call.callee.name.origin == "add"
    assert call.arguments == [LiteralExpr(1.0), LiteralExpr(2.0)]


class TestFunctionErrorPropagation:
    def test_function_declaration_missing_name_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("Func () { return 1; }")

    def test_function_declaration_missing_left_paren_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("Func add a, b) { return a + b; }")

    def test_function_declaration_missing_right_paren_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("Func add(a, b { return a + b; }")

    def test_function_declaration_missing_body_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("Func add(a, b);")

    def test_function_call_missing_closing_paren_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("add(1, 2;")

    def test_function_call_missing_semicolon_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("add(1, 2)")


# ─────────────────────────────────────────────────────────
# 오류 전파 — Tokenizer / Parser 오류가 Assembler를 통해 그대로 올라온다
# ─────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────
# Class — 선언 / 필드 / 메서드 / This / instanceof
# ─────────────────────────────────────────────────────────


def test_empty_class_declaration():
    # Class Robot { }
    stmts = assemble("Class Robot { }")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ClassDeclStmt)
    assert stmt.name.origin == "Robot"
    assert stmt.superclass is None
    assert stmt.methods == []


def test_class_declaration_with_method():
    # Class Robot { Func move(dist) { return dist; } }
    stmts = assemble("Class Robot { Func move(dist) { return dist; } }")

    stmt = stmts[0]
    assert isinstance(stmt, ClassDeclStmt)
    assert stmt.name.origin == "Robot"
    assert len(stmt.methods) == 1
    method = stmt.methods[0]
    assert isinstance(method, FuncDeclStmt)
    assert method.name.origin == "move"
    assert [p.origin for p in method.params] == ["dist"]


def test_class_with_superclass():
    # Class SpeedRobot : Robot { }
    stmts = assemble("Class SpeedRobot : Robot { }")

    stmt = stmts[0]
    assert isinstance(stmt, ClassDeclStmt)
    assert stmt.name.origin == "SpeedRobot"
    assert stmt.superclass is not None
    assert isinstance(stmt.superclass, VariableExpr)
    assert stmt.superclass.name.origin == "Robot"


def test_get_expr():
    # print r.speed;
    expr = assemble_print("print r.speed;")

    assert isinstance(expr, GetExpr)
    assert isinstance(expr.object, VariableExpr)
    assert expr.object.name.origin == "r"
    assert expr.name.origin == "speed"


def test_set_expr():
    # r.speed = 10;
    stmts = assemble("r.speed = 10;")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, ExpressionStmt)
    expr = stmt.expression
    assert isinstance(expr, SetExpr)
    assert isinstance(expr.object, VariableExpr)
    assert expr.object.name.origin == "r"
    assert expr.name.origin == "speed"
    assert expr.value == LiteralExpr(10.0)


def test_this_expr():
    # Class Robot { Func getX() { return This.x; } }
    stmts = assemble("Class Robot { Func getX() { return This.x; } }")

    method = stmts[0].methods[0]
    ret = method.body[0]
    get_expr = ret.value
    assert isinstance(get_expr, GetExpr)
    assert isinstance(get_expr.object, ThisExpr)
    assert get_expr.name.origin == "x"


def test_instanceof_expr():
    # print r instanceof Robot;
    expr = assemble_print("print r instanceof Robot;")

    assert isinstance(expr, InstanceOfExpr)
    assert isinstance(expr.object, VariableExpr)
    assert expr.object.name.origin == "r"
    assert expr.klass.origin == "Robot"


def test_chained_method_call():
    # r.move(5);
    stmts = assemble("r.move(5);")

    stmt = stmts[0]
    assert isinstance(stmt, ExpressionStmt)
    call = stmt.expression
    assert isinstance(call, CallExpr)
    assert isinstance(call.callee, GetExpr)
    assert call.callee.name.origin == "move"
    assert call.arguments == [LiteralExpr(5.0)]


def test_class_instance_creation():
    # var r = Robot();
    stmts = assemble("var r = Robot();")

    stmt = stmts[0]
    assert isinstance(stmt, VarDeclStmt)
    call = stmt.initializer
    assert isinstance(call, CallExpr)
    assert isinstance(call.callee, VariableExpr)
    assert call.callee.name.origin == "Robot"
    assert call.arguments == []


class TestErrorPropagation:
    def test_unknown_character_raises_tokenize_error(self):
        with pytest.raises(TokenizeError):
            assemble("@invalid;")

    def test_unclosed_string_raises_tokenize_error(self):
        with pytest.raises(TokenizeError):
            assemble('print "hello;')

    def test_missing_semicolon_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("var a = 10")

    def test_missing_expression_raises_parse_error(self):
        with pytest.raises(ParseError):
            assemble("print ;")
