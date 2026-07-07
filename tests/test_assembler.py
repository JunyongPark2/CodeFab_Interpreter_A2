# test_assembler.py — Assembler(Tokenizer + Parser) 통합 유닛 테스트 (TDD: 구현 전 작성)
#
# 실행: pytest test_assembler.py -v
#
# Assembler는 Tokenizer/Parser "클래스"를 생성 시점에 외부에서 주입받고,
# assemble(text) 호출 시 내부적으로 Tokenizer(text).tokenize() → Parser(tokens).parse()
# 순서로 실행해 list[Stmt] (AST)를 돌려주는 파사드다.
#
#   assembler = Assembler(Tokenizer, Parser)
#   stmts = assembler.assemble(source)
#
# test_parser.py가 손으로 만든 토큰 목록으로 트리 "모양"만 검사했다면,
# 여기서는 실제 소스 코드 문자열을 넣었을 때 동일한 트리가 나오는지,
# 그리고 Tokenizer/Parser의 오류가 Assembler를 통해 잘 전파되는지를 검사한다.
# (Parser와 마찬가지로 계산은 하지 않는다 — 계산은 Executor의 몫.)

import pytest

from interpreter.assembler import Assembler
from interpreter.ast_nodes import (
    LiteralExpr, BinaryExpr, UnaryExpr, GroupingExpr,
    VariableExpr, AssignExpr,
    PrintStmt, ExpressionStmt, VarDeclStmt, BlockStmt,
    IfStmt, ForStmt,
)
from interpreter.parser import Parser, ParseError
from interpreter.tokenizer import Tokenizer, TokenizeError
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

def test_assembler는_tokenizer와_parser_클래스를_주입받아_재사용_가능하다():
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

def test_곱셈이_덧셈보다_먼저():
    # print 1 + 2 * 3;
    expr = assemble_print("print 1 + 2 * 3;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS  # 루트는 +
    assert expr.left == LiteralExpr(1.0)

    assert isinstance(expr.right, BinaryExpr)  # 오른쪽은 2 * 3
    assert expr.right.operator.type == TokenType.STAR
    assert expr.right.left == LiteralExpr(2.0)
    assert expr.right.right == LiteralExpr(3.0)


def test_괄호가_우선순위를_이긴다():
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


def test_뺄셈은_왼쪽부터_묶인다():
    # print 10 - 4 - 3;
    expr = assemble_print("print 10 - 4 - 3;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.MINUS
    assert expr.right == LiteralExpr(3.0)

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 10 - 4
    assert expr.left.operator.type == TokenType.MINUS
    assert expr.left.left == LiteralExpr(10.0)
    assert expr.left.right == LiteralExpr(4.0)


def test_나눗셈은_왼쪽부터_묶인다():
    # print 8 / 2 / 2;
    expr = assemble_print("print 8 / 2 / 2;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.SLASH
    assert expr.right == LiteralExpr(2.0)

    assert isinstance(expr.left, BinaryExpr)  # 왼쪽은 8 / 2
    assert expr.left.operator.type == TokenType.SLASH
    assert expr.left.left == LiteralExpr(8.0)
    assert expr.left.right == LiteralExpr(2.0)


def test_단항_마이너스는_덧셈보다_먼저():
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

def test_비교_작다():
    # print 1 < 2;
    expr = assemble_print("print 1 < 2;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.LESS
    assert expr.left == LiteralExpr(1.0)
    assert expr.right == LiteralExpr(2.0)


def test_비교_크다():
    # print 3 > 5;
    expr = assemble_print("print 3 > 5;")

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.GREATER
    assert expr.left == LiteralExpr(3.0)
    assert expr.right == LiteralExpr(5.0)


def test_문자열_연결():
    # print "Hello, " + "CodeFab!";
    expr = assemble_print('print "Hello, " + "CodeFab!";')

    assert isinstance(expr, BinaryExpr)
    assert expr.operator.type == TokenType.PLUS
    assert expr.left == LiteralExpr("Hello, ")
    assert expr.right == LiteralExpr("CodeFab!")


def test_불리언_참():
    # print true;
    assert assemble_print("print true;") == LiteralExpr(True)


def test_불리언_거짓():
    # print false;
    assert assemble_print("print false;") == LiteralExpr(False)


# ─────────────────────────────────────────────────────────
# 변수 선언 / 재할당 / 블록 스코프 / 섀도잉
# ─────────────────────────────────────────────────────────

def test_var_선언():
    # var a = 10;
    stmts = assemble("var a = 10;")

    assert len(stmts) == 1
    stmt = stmts[0]
    assert isinstance(stmt, VarDeclStmt)
    assert stmt.name.origin == "a"
    assert stmt.initializer == LiteralExpr(10.0)


def test_선언_후_변수_참조():
    # var a = 10; var b = 20; print a + b;   // expect: 30
    stmts = assemble(
        'var a = 10;\n'
        'var b = 20;\n'
        'print a + b;            // expect: 30\n'
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


def test_재할당():
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


def test_블록_스코프_및_섀도잉():
    # var x = "global";
    # { var x = "inner"; print x; }   // expect: inner
    # print x;                        // expect: global
    stmts = assemble(
        'var x = "global";\n'
        '{\n'
        '  var x = "inner";\n'
        '  print x;              // expect: inner\n'
        '}\n'
        'print x;                // expect: global\n'
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


def test_블록_안에서_바깥_변수_수정():
    # var count = 0;
    # { count = count + 1; }
    # print count;            // expect: 1
    stmts = assemble(
        'var count = 0;\n'
        '{\n'
        '  count = count + 1;    // 같은 이름 재선언이 아니라 바깥 변수 수정\n'
        '}\n'
        'print count;            // expect: 1\n'
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


def test_중첩_스코프():
    # var outer = "A";
    # { var inner = "B"; { print outer + inner; } }   // expect: AB
    stmts = assemble(
        'var outer = "A";\n'
        '{\n'
        '  var inner = "B";\n'
        '  {\n'
        '    print outer + inner;  // expect: AB\n'
        '  }\n'
        '}\n'
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

def test_if_참_단순():
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


def test_dangling_else_가장_가까운_if에_결합():
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


def test_for_반복문():
    # for (var j = 0; j < 3; j = j + 1) { print j; }
    stmts = assemble('for (var j = 0; j < 3; j = j + 1) { print j; }')

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
    def test_선언_재할당_블록스코프_전체_스크립트(self):
        source = '''\
// --- 선언 & 사용 ---
var a = 10;
var b = 20;
print a + b;            // expect: 30

// --- 재할당 ---
a = a + 5;
print a;                // expect: 15
'''
        stmts = assemble(source)

        assert len(stmts) == 5
        assert isinstance(stmts[0], VarDeclStmt) and stmts[0].name.origin == "a"
        assert isinstance(stmts[1], VarDeclStmt) and stmts[1].name.origin == "b"
        assert isinstance(stmts[2], PrintStmt)
        assert isinstance(stmts[3], ExpressionStmt)
        assert isinstance(stmts[3].expression, AssignExpr)
        assert isinstance(stmts[4], PrintStmt)

    def test_제어흐름_전체_스크립트(self):
        source = '''\
if (true) print "bbq";

if (false) print "no"; else print "kfc";

for (var j = 0; j < 3; j = j + 1) { print j; }
'''
        stmts = assemble(source)

        assert len(stmts) == 3
        assert isinstance(stmts[0], IfStmt)
        assert stmts[0].else_branch is None
        assert isinstance(stmts[1], IfStmt)
        assert stmts[1].else_branch is not None
        assert isinstance(stmts[2], ForStmt)

    def test_빈_소스는_빈_문장_목록(self):
        assert assemble("") == []


# ─────────────────────────────────────────────────────────
# 오류 전파 — Tokenizer / Parser 오류가 Assembler를 통해 그대로 올라온다
# ─────────────────────────────────────────────────────────

class TestErrorPropagation:
    def test_인식할_수_없는_문자는_TokenizeError(self):
        with pytest.raises(TokenizeError):
            assemble("@invalid;")

    def test_닫히지_않은_문자열은_TokenizeError(self):
        with pytest.raises(TokenizeError):
            assemble('print "hello;')

    def test_세미콜론_누락은_ParseError(self):
        with pytest.raises(ParseError):
            assemble("var a = 10")

    def test_표현식_누락은_ParseError(self):
        with pytest.raises(ParseError):
            assemble("print ;")
