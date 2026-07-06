import pytest
from tokenizer import Tokenizer
from tokens import TokenType


# ── 헬퍼 ──────────────────────────────────────────────────────────────

def tokenize(source: str):
    return Tokenizer(source).tokenize()


def as_token_tuples(tokens):
    """각 토큰을 (type, text, value) 튜플 목록으로 변환."""
    return [(t.type, t.text, t.value) for t in tokens]



# ── 산술 / 연산자 우선순위 ─────────────────────────────────────────────

class TestArithmetic:
    def test_add_and_multiply(self):
        # print 1 + 2 * 3;
        assert as_token_tuples(tokenize("print 1 + 2 * 3;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.NUMBER,    "1",     1.0),
            (TokenType.PLUS,      "+",     None),
            (TokenType.NUMBER,    "2",     2.0),
            (TokenType.STAR,      "*",     None),
            (TokenType.NUMBER,    "3",     3.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]

    def test_parenthesized_add_then_multiply(self):
        # print (1 + 2) * 3;
        assert as_token_tuples(tokenize("print (1 + 2) * 3;")) == [
            (TokenType.PRINT,       "print", None),
            (TokenType.LEFT_PAREN,  "(",     None),
            (TokenType.NUMBER,      "1",     1.0),
            (TokenType.PLUS,        "+",     None),
            (TokenType.NUMBER,      "2",     2.0),
            (TokenType.RIGHT_PAREN, ")",     None),
            (TokenType.STAR,        "*",     None),
            (TokenType.NUMBER,      "3",     3.0),
            (TokenType.SEMICOLON,   ";",     None),
            (TokenType.EOF,         "",      None),
        ]

    def test_left_associative_subtraction(self):
        # print 10 - 4 - 3;
        assert as_token_tuples(tokenize("print 10 - 4 - 3;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.NUMBER,    "10",    10.0),
            (TokenType.MINUS,     "-",     None),
            (TokenType.NUMBER,    "4",     4.0),
            (TokenType.MINUS,     "-",     None),
            (TokenType.NUMBER,    "3",     3.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]

    def test_left_associative_division(self):
        # print 8 / 2 / 2;
        assert as_token_tuples(tokenize("print 8 / 2 / 2;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.NUMBER,    "8",     8.0),
            (TokenType.SLASH,     "/",     None),
            (TokenType.NUMBER,    "2",     2.0),
            (TokenType.SLASH,     "/",     None),
            (TokenType.NUMBER,    "2",     2.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]

    def test_unary_minus_is_separate_token(self):
        # print -3 + 2;
        # '-'는 단항 연산자가 아닌 독립 MINUS 토큰으로 분리된다.
        assert as_token_tuples(tokenize("print -3 + 2;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.MINUS,     "-",     None),
            (TokenType.NUMBER,    "3",     3.0),
            (TokenType.PLUS,      "+",     None),
            (TokenType.NUMBER,    "2",     2.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]


# ── 비교 연산자 ────────────────────────────────────────────────────────

class TestComparison:
    def test_less_than(self):
        # print 1 < 2;
        assert as_token_tuples(tokenize("print 1 < 2;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.NUMBER,    "1",     1.0),
            (TokenType.LESS,      "<",     None),
            (TokenType.NUMBER,    "2",     2.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]

    def test_greater_than(self):
        # print 3 > 5;
        assert as_token_tuples(tokenize("print 3 > 5;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.NUMBER,    "3",     3.0),
            (TokenType.GREATER,   ">",     None),
            (TokenType.NUMBER,    "5",     5.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]


# ── 문자열 연결 ────────────────────────────────────────────────────────

class TestStringLiterals:
    def test_string_concatenation(self):
        # print "Hello, " + "CodeFab!";
        # text는 따옴표 포함, value는 따옴표 제외 내용
        assert as_token_tuples(tokenize('print "Hello, " + "CodeFab!";')) == [
            (TokenType.PRINT,     "print",       None),
            (TokenType.STRING,    '"Hello, "',   "Hello, "),
            (TokenType.PLUS,      "+",           None),
            (TokenType.STRING,    '"CodeFab!"',  "CodeFab!"),
            (TokenType.SEMICOLON, ";",           None),
            (TokenType.EOF,       "",            None),
        ]


# ── 숫자 리터럴 포맷 ──────────────────────────────────────────────────

class TestNumberLiterals:
    def test_integer(self):
        # print 5;  — text="5", value=5.0
        assert as_token_tuples(tokenize("print 5;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.NUMBER,    "5",     5.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]

    def test_integer_dot_zero(self):
        # print 5.0;  — text="5.0", value=5.0
        assert as_token_tuples(tokenize("print 5.0;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.NUMBER,    "5.0",   5.0),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]

    def test_float(self):
        # print 3.14;  — value는 float 근사 비교
        tokens = tokenize("print 3.14;")
        num = next(t for t in tokens if t.type == TokenType.NUMBER)
        assert num.text  == "3.14"
        assert num.value == pytest.approx(3.14)

    def test_integer_and_float_text_differ(self):
        # 5와 5.0은 value는 동일하지만 text는 다르다.
        tok_int   = next(t for t in tokenize("5;")   if t.type == TokenType.NUMBER)
        tok_float = next(t for t in tokenize("5.0;") if t.type == TokenType.NUMBER)
        assert tok_int.value == tok_float.value  # 5.0 == 5.0
        assert tok_int.text  != tok_float.text   # "5" != "5.0"


# ── boolean 리터럴 ─────────────────────────────────────────────────────

class TestBooleanLiterals:
    def test_true(self):
        # print true;
        assert as_token_tuples(tokenize("print true;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.TRUE,      "true",  None),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]

    def test_false(self):
        # print false;
        assert as_token_tuples(tokenize("print false;")) == [
            (TokenType.PRINT,     "print", None),
            (TokenType.FALSE,     "false", None),
            (TokenType.SEMICOLON, ";",     None),
            (TokenType.EOF,       "",      None),
        ]


# ── EOF 토큰 ──────────────────────────────────────────────────────────

class TestEOF:
    def test_eof_always_last(self):
        tokens = tokenize("print 1;")
        assert tokens[-1].type  == TokenType.EOF
        assert tokens[-1].text  == ""
        assert tokens[-1].value is None

    def test_empty_source_only_eof(self):
        tokens = tokenize("")
        assert len(tokens) == 1
        assert tokens[0].type == TokenType.EOF


# ── 줄 번호 추적 ──────────────────────────────────────────────────────

class TestLineTracking:
    def test_single_line(self):
        tokens = tokenize("print 1;")
        assert all(t.line == 1 for t in tokens if t.type != TokenType.EOF)

    def test_multiline_increments(self):
        source = "print 1;\nprint 2;"
        tokens = tokenize(source)
        print(tokens)
        first_print  = tokens[0]
        second_print = next(t for t in tokens[3:] if t.type == TokenType.PRINT)
        assert first_print.line  == 1
        assert second_print.line == 2


# ── 오류 처리 ──────────────────────────────────────────────────────────
#
# class TestErrors:
#     def test_unknown_character_raises(self):
#         with pytest.raises(TokenizeError):
#             tokenize("@invalid")
#
#     def test_unclosed_string_raises(self):
#         with pytest.raises(TokenizeError):
#             tokenize('"hello')
#
#     def test_tokenize_error_includes_line_number(self):
#         with pytest.raises(TokenizeError, match=r"\[1번째줄\]"):
#             tokenize("@")


# ── 변수 선언 / 재할당 / 블록 스코프 스크립트 토큰화 ───────────────────────

class TestVariableDeclarationAndUse:
    def test_declare_and_use(self):
        # var a = 10;
        # var b = 20;
        # print a + b;            // expect: 30
        source = (
            'var a = 10;\n'
            'var b = 20;\n'
            'print a + b;            // expect: 30\n'
        )
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.VAR,        "var",   None),
            (TokenType.IDENTIFIER, "a",     None),
            (TokenType.EQUAL,      "=",     None),
            (TokenType.NUMBER,     "10",    10.0),
            (TokenType.SEMICOLON,  ";",     None),
            (TokenType.VAR,        "var",   None),
            (TokenType.IDENTIFIER, "b",     None),
            (TokenType.EQUAL,      "=",     None),
            (TokenType.NUMBER,     "20",    20.0),
            (TokenType.SEMICOLON,  ";",     None),
            (TokenType.PRINT,      "print", None),
            (TokenType.IDENTIFIER, "a",     None),
            (TokenType.PLUS,       "+",     None),
            (TokenType.IDENTIFIER, "b",     None),
            (TokenType.SEMICOLON,  ";",     None),
            (TokenType.EOF,        "",      None),
        ]

    def test_line_comment_after_statement_is_ignored(self):
        # 주석 뒤 내용("expect: 30")이 토큰으로 새어나오면 안 된다.
        tokens = tokenize("print a + b;            // expect: 30\n")
        assert TokenType.NUMBER not in [t.type for t in tokens]
        assert tokens[-1].type == TokenType.EOF


class TestReassignment:
    def test_reassign_and_print(self):
        # a = a + 5;
        # print a;                // expect: 15
        source = (
            'a = a + 5;\n'
            'print a;                // expect: 15\n'
        )
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.IDENTIFIER, "a", None),
            (TokenType.EQUAL,      "=", None),
            (TokenType.IDENTIFIER, "a", None),
            (TokenType.PLUS,       "+", None),
            (TokenType.NUMBER,     "5", 5.0),
            (TokenType.SEMICOLON,  ";", None),
            (TokenType.PRINT,   "print", None),
            (TokenType.IDENTIFIER, "a", None),
            (TokenType.SEMICOLON,  ";", None),
            (TokenType.EOF,        "", None),
        ]


class TestBlockScopeShadowing:
    def test_shadowed_block_and_outer_access(self):
        # var x = "global";
        # {
        #   var x = "inner";
        #   print x;              // expect: inner
        # }
        # print x;                // expect: global  (블록 밖은 영향 없음)
        source = (
            'var x = "global";\n'
            '{\n'
            '  var x = "inner";\n'
            '  print x;              // expect: inner\n'
            '}\n'
            'print x;                // expect: global  (블록 밖은 영향 없음)\n'
        )
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.VAR,         "var",       None),
            (TokenType.IDENTIFIER,  "x",         None),
            (TokenType.EQUAL,       "=",         None),
            (TokenType.STRING,      '"global"',  "global"),
            (TokenType.SEMICOLON,   ";",         None),
            (TokenType.LEFT_BRACE,  "{",         None),
            (TokenType.VAR,         "var",       None),
            (TokenType.IDENTIFIER,  "x",         None),
            (TokenType.EQUAL,       "=",         None),
            (TokenType.STRING,      '"inner"',   "inner"),
            (TokenType.SEMICOLON,   ";",         None),
            (TokenType.PRINT,       "print",     None),
            (TokenType.IDENTIFIER,  "x",         None),
            (TokenType.SEMICOLON,   ";",         None),
            (TokenType.RIGHT_BRACE, "}",         None),
            (TokenType.PRINT,       "print",     None),
            (TokenType.IDENTIFIER,  "x",         None),
            (TokenType.SEMICOLON,   ";",         None),
            (TokenType.EOF,         "",          None),
        ]

    def test_inner_block_line_numbers(self):
        source = (
            'var x = "global";\n'   # line 1
            '{\n'                   # line 2
            '  var x = "inner";\n'  # line 3
            '  print x;\n'          # line 4
            '}\n'                   # line 5
            'print x;\n'            # line 6
        )
        tokens = tokenize(source)
        inner_prints = [t for t in tokens if t.type == TokenType.PRINT]
        assert inner_prints[0].line == 4
        assert inner_prints[1].line == 6


class TestOuterVariableMutationInBlock:
    def test_mutate_outer_variable_inside_block(self):
        # var count = 0;
        # {
        #   count = count + 1;    // 같은 이름 재선언이 아니라 바깥 변수 수정
        # }
        # print count;            // expect: 1
        source = (
            'var count = 0;\n'
            '{\n'
            '  count = count + 1;    // 같은 이름 재선언이 아니라 바깥 변수 수정\n'
            '}\n'
            'print count;            // expect: 1\n'
        )
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.VAR,         "var",   None),
            (TokenType.IDENTIFIER,  "count", None),
            (TokenType.EQUAL,       "=",     None),
            (TokenType.NUMBER,      "0",     0.0),
            (TokenType.SEMICOLON,   ";",     None),
            (TokenType.LEFT_BRACE,  "{",     None),
            (TokenType.IDENTIFIER,  "count", None),
            (TokenType.EQUAL,       "=",     None),
            (TokenType.IDENTIFIER,  "count", None),
            (TokenType.PLUS,        "+",     None),
            (TokenType.NUMBER,      "1",     1.0),
            (TokenType.SEMICOLON,   ";",     None),
            (TokenType.RIGHT_BRACE, "}",     None),
            (TokenType.PRINT,       "print", None),
            (TokenType.IDENTIFIER,  "count", None),
            (TokenType.SEMICOLON,   ";",     None),
            (TokenType.EOF,         "",      None),
        ]


class TestNestedScopeResolution:
    def test_nested_block_variable_concat(self):
        # var outer = "A";
        # {
        #   var inner = "B";
        #   {
        #     print outer + inner;  // expect: AB
        #   }
        # }
        source = (
            'var outer = "A";\n'
            '{\n'
            '  var inner = "B";\n'
            '  {\n'
            '    print outer + inner;  // expect: AB\n'
            '  }\n'
            '}\n'
        )
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.VAR,         "var",     None),
            (TokenType.IDENTIFIER,  "outer",   None),
            (TokenType.EQUAL,       "=",       None),
            (TokenType.STRING,      '"A"',     "A"),
            (TokenType.SEMICOLON,   ";",       None),
            (TokenType.LEFT_BRACE,  "{",       None),
            (TokenType.VAR,         "var",     None),
            (TokenType.IDENTIFIER,  "inner",   None),
            (TokenType.EQUAL,       "=",       None),
            (TokenType.STRING,      '"B"',     "B"),
            (TokenType.SEMICOLON,   ";",       None),
            (TokenType.LEFT_BRACE,  "{",       None),
            (TokenType.PRINT,       "print",   None),
            (TokenType.IDENTIFIER,  "outer",   None),
            (TokenType.PLUS,        "+",       None),
            (TokenType.IDENTIFIER,  "inner",   None),
            (TokenType.SEMICOLON,   ";",       None),
            (TokenType.RIGHT_BRACE, "}",       None),
            (TokenType.RIGHT_BRACE, "}",       None),
            (TokenType.EOF,         "",        None),
        ]


class TestFullScriptTokenization:
    def test_full_script_has_no_leftover_comment_tokens(self):
        source = '''\
// --- 선언 & 사용 ---
var a = 10;
var b = 20;
print a + b;            // expect: 30


// --- 재할당 ---
a = a + 5;
print a;                // expect: 15

// --- 블록 스코프 & 변수 shadowing ---

var x = "global";
{
  var x = "inner";
  print x;              // expect: inner
}
print x;                // expect: global  (블록 밖은 영향 없음)


// --- 안쪽 블록에서 바깥 변수 수정은 가능 ---

var count = 0;
{
  count = count + 1;    // 같은 이름 재선언이 아니라 바깥 변수 수정
}
print count;            // expect: 1


// 중첩 스코프 해석

var outer = "A";
{
  var inner = "B";
  {
    print outer + inner;  // expect: AB
  }
}
'''
        tokens = tokenize(source)

        # 마지막 토큰은 항상 EOF
        assert tokens[-1].type == TokenType.EOF

        # 주석 내용("선언", "재할당", "expect" 등)이 토큰으로 남아있으면 안 된다.
        identifiers = {t.text for t in tokens if t.type == TokenType.IDENTIFIER}
        assert identifiers == {"a", "b", "x", "count", "outer", "inner"}

        # 여는/닫는 중괄호 개수가 일치해야 한다 (블록 4개).
        left_braces  = [t for t in tokens if t.type == TokenType.LEFT_BRACE]
        right_braces = [t for t in tokens if t.type == TokenType.RIGHT_BRACE]
        assert len(left_braces) == len(right_braces) == 4

        # var 선언은 총 6번 (a, b, x, x(inner block), count, outer, inner) → 실제로는 7번
        var_tokens = [t for t in tokens if t.type == TokenType.VAR]
        assert len(var_tokens) == 7

    def test_full_script_line_numbers_for_print_statements(self):
        source = '''\
// --- 선언 & 사용 ---
var a = 10;
var b = 20;
print a + b;            // expect: 30


// --- 재할당 ---
a = a + 5;
print a;                // expect: 15
'''
        tokens = tokenize(source)
        print_lines = [t.line for t in tokens if t.type == TokenType.PRINT]
        assert print_lines == [4, 9]


# ── 제어 흐름 (if / else / for) 스크립트 토큰화 ──────────────────────────

class TestIfElse:
    def test_if_without_else(self):
        # if (true) print "bbq";
        source = 'if (true) print "bbq";\n'
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.IF,          "if",     None),
            (TokenType.LEFT_PAREN,  "(",      None),
            (TokenType.TRUE,        "true",   None),
            (TokenType.RIGHT_PAREN, ")",      None),
            (TokenType.PRINT,       "print",  None),
            (TokenType.STRING,      '"bbq"',  "bbq"),
            (TokenType.SEMICOLON,   ";",      None),
            (TokenType.EOF,         "",       None),
        ]

    def test_if_else(self):
        # if (false) print "no"; else print "kfc";
        source = 'if (false) print "no"; else print "kfc";\n'
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.IF,          "if",     None),
            (TokenType.LEFT_PAREN,  "(",      None),
            (TokenType.FALSE,       "false",  None),
            (TokenType.RIGHT_PAREN, ")",      None),
            (TokenType.PRINT,       "print",  None),
            (TokenType.STRING,      '"no"',   "no"),
            (TokenType.SEMICOLON,   ";",      None),
            (TokenType.ELSE,        "else",   None),
            (TokenType.PRINT,       "print",  None),
            (TokenType.STRING,      '"kfc"',  "kfc"),
            (TokenType.SEMICOLON,   ";",      None),
            (TokenType.EOF,         "",       None),
        ]


class TestDanglingElseTokenization:
    def test_nested_if_else_inside_block(self):
        # if (true)
        # {
        #   if (false) print "kfc";
        #   else print "bbq";
        # }
        source = (
            'if (true)\n'
            '{\n'
            '  if (false) print "kfc";\n'
            '  else print "bbq";\n'
            '}\n'
        )
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.IF,          "if",      None),
            (TokenType.LEFT_PAREN,  "(",       None),
            (TokenType.TRUE,        "true",    None),
            (TokenType.RIGHT_PAREN, ")",       None),
            (TokenType.LEFT_BRACE,  "{",       None),
            (TokenType.IF,          "if",      None),
            (TokenType.LEFT_PAREN,  "(",       None),
            (TokenType.FALSE,       "false",   None),
            (TokenType.RIGHT_PAREN, ")",       None),
            (TokenType.PRINT,       "print",   None),
            (TokenType.STRING,      '"kfc"',   "kfc"),
            (TokenType.SEMICOLON,   ";",       None),
            (TokenType.ELSE,        "else",    None),
            (TokenType.PRINT,       "print",   None),
            (TokenType.STRING,      '"bbq"',   "bbq"),
            (TokenType.SEMICOLON,   ";",       None),
            (TokenType.RIGHT_BRACE, "}",       None),
            (TokenType.EOF,         "",        None),
        ]

    def test_inner_if_and_else_are_on_expected_lines(self):
        source = (
            'if (true)\n'           # line 1
            '{\n'                   # line 2
            '  if (false) print "kfc";\n'  # line 3
            '  else print "bbq";\n'        # line 4
            '}\n'                   # line 5
        )
        tokens = tokenize(source)
        if_tokens = [t for t in tokens if t.type == TokenType.IF]
        else_tokens = [t for t in tokens if t.type == TokenType.ELSE]
        assert [t.line for t in if_tokens] == [1, 3]
        assert [t.line for t in else_tokens] == [4]


class TestForLoop:
    def test_for_loop_tokenization(self):
        # for (var j = 0; j < 3; j = j + 1) { print j; }
        source = 'for (var j = 0; j < 3; j = j + 1) { print j; }\n'
        assert as_token_tuples(tokenize(source)) == [
            (TokenType.FOR,          "for",  None),
            (TokenType.LEFT_PAREN,   "(",    None),
            (TokenType.VAR,          "var",  None),
            (TokenType.IDENTIFIER,   "j",    None),
            (TokenType.EQUAL,        "=",    None),
            (TokenType.NUMBER,       "0",    0.0),
            (TokenType.SEMICOLON,    ";",    None),
            (TokenType.IDENTIFIER,   "j",    None),
            (TokenType.LESS,         "<",    None),
            (TokenType.NUMBER,       "3",    3.0),
            (TokenType.SEMICOLON,    ";",    None),
            (TokenType.IDENTIFIER,   "j",    None),
            (TokenType.EQUAL,        "=",    None),
            (TokenType.IDENTIFIER,   "j",    None),
            (TokenType.PLUS,         "+",    None),
            (TokenType.NUMBER,       "1",    1.0),
            (TokenType.RIGHT_PAREN,  ")",    None),
            (TokenType.LEFT_BRACE,   "{",    None),
            (TokenType.PRINT,        "print", None),
            (TokenType.IDENTIFIER,   "j",    None),
            (TokenType.SEMICOLON,    ";",    None),
            (TokenType.RIGHT_BRACE,  "}",    None),
            (TokenType.EOF,          "",     None),
        ]

    def test_for_loop_condition_and_increment_use_same_identifier(self):
        source = 'for (var j = 0; j < 3; j = j + 1) { print j; }\n'
        tokens = tokenize(source)
        j_tokens = [t for t in tokens if t.type == TokenType.IDENTIFIER]
        assert all(t.text == "j" for t in j_tokens)
        assert len(j_tokens) == 5  # 초기화, 조건, 증감(좌변+우변 2개), 바디


class TestControlFlowFullScript:
    def test_full_control_flow_script(self):
        source = '''\
if (true) print "bbq";

if (false) print "no"; else print "kfc";

if (true)
{
  if (false) print "kfc";
  else print "bbq";
}

for (var j = 0; j < 3; j = j + 1) { print j; }
'''
        tokens = tokenize(source)

        assert tokens[-1].type == TokenType.EOF

        # if / else / for 키워드 등장 횟수
        assert sum(1 for t in tokens if t.type == TokenType.IF) == 4
        assert sum(1 for t in tokens if t.type == TokenType.ELSE) == 2
        assert sum(1 for t in tokens if t.type == TokenType.FOR) == 1

        # 괄호와 중괄호 짝이 맞아야 한다.
        assert sum(1 for t in tokens if t.type == TokenType.LEFT_PAREN) == \
            sum(1 for t in tokens if t.type == TokenType.RIGHT_PAREN)
        assert sum(1 for t in tokens if t.type == TokenType.LEFT_BRACE) == \
            sum(1 for t in tokens if t.type == TokenType.RIGHT_BRACE)

        # 문자열 리터럴 값 집합 확인
        strings = {t.value for t in tokens if t.type == TokenType.STRING}
        assert strings == {"bbq", "no", "kfc"}
