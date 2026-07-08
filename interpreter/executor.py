from .ast_nodes import (
    ArrayExpr,
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDeclStmt,
    GroupingExpr,
    IfStmt,
    IndexGetExpr,
    IndexSetExpr,
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    ReturnStmt,
    Stmt,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from .environment import Environment
from .errors import LangRuntimeError
from .tokens import TokenType


class ReturnSignal(Exception):
    """return 실행 시 함수 호출 프레임까지 한 번에 빠져나오기 위한 내부 제어 신호."""

    def __init__(self, value):
        self.value = value


class LangFunction:
    """Func 선언으로 만들어지는 런타임 함수 값. 정의 시점의 Environment를 closure로 캡처해서
    재귀 호출(자기 자신을 다시 참조) 시에도 이름을 찾을 수 있게 한다."""

    def __init__(self, decl: FuncDeclStmt, closure: Environment):
        self.decl = decl
        self.closure = closure

    @property
    def arity(self) -> int:
        return len(self.decl.params)

    def call(self, executor: "Executor", arguments: list):
        env = Environment(parent=self.closure)
        for param, value in zip(self.decl.params, arguments):
            env.define(param.origin, value)
        try:
            executor._exec_block(self.decl.body, env)
        except ReturnSignal as signal:
            return signal.value
        return None


class Executor:
    def __init__(
        self,
        stmts: list[Stmt],
        environment: Environment | None = None,
        locals: dict[int, int] | None = None,
    ):
        # environment를 넘기지 않으면 매번 새 전역 스코프로 시작한다 (기존 동작 그대로 유지).
        # REPL처럼 "이전 실행에서 선언한 변수를 다음 실행에서도 써야 하는" 경우엔
        # 같은 Environment 인스턴스를 계속 넘겨서 재사용한다 (CodeFabInterpreter 참고).
        self._stmts = stmts
        self._global = environment if environment is not None else Environment()
        self._current = self._global
        # Checker.check()가 계산해둔 정적 바인딩 결과 (id(expr) -> distance).
        # 여기 없는 변수 참조는 기존처럼 Environment 체인을 동적으로 거슬러 올라간다.
        self._locals = locals if locals is not None else {}
        self._stmt_handlers = {
            PrintStmt: self._exec_print,
            VarDeclStmt: self._exec_var_decl,
            ExpressionStmt: self._exec_expression,
            BlockStmt: self._exec_block_stmt,
            IfStmt: self._exec_if,
            ForStmt: self._exec_for,
            FuncDeclStmt: self._exec_func_decl,
            ReturnStmt: self._exec_return,
        }
        self._expr_handlers = {
            LiteralExpr: self._eval_literal,
            VariableExpr: self._eval_variable,
            AssignExpr: self._eval_assign,
            GroupingExpr: self._eval_grouping,
            UnaryExpr: self._eval_unary,
            BinaryExpr: self._eval_binary,
            LogicalExpr: self._eval_logical,
            CallExpr: self._eval_call,
            ArrayExpr: self._eval_array,
            IndexGetExpr: self._eval_index_get,
            IndexSetExpr: self._eval_index_set,
        }

    def execute(self) -> None:
        for stmt in self._stmts:
            self._exec_stmt(stmt)

    # ── Stmt 실행 ─────────────────────────────────────────
    def _exec_stmt(self, stmt: Stmt) -> None:
        handler = self._stmt_handlers.get(type(stmt))
        if handler:
            handler(stmt)

    def _exec_print(self, stmt: PrintStmt) -> None:
        print(self._stringify(self._eval(stmt.expression)))

    def _exec_var_decl(self, stmt: VarDeclStmt) -> None:
        val = self._eval(stmt.initializer) if stmt.initializer else None
        self._current.define(stmt.name.origin, val)

    def _exec_expression(self, stmt: ExpressionStmt) -> None:
        self._eval(stmt.expression)

    def _exec_block_stmt(self, stmt: BlockStmt) -> None:
        self._exec_block(stmt.statements, Environment(parent=self._current))

    def _exec_if(self, stmt: IfStmt) -> None:
        if self._is_truthy(self._eval(stmt.condition)):
            self._exec_stmt(stmt.then_branch)
        elif stmt.else_branch:
            self._exec_stmt(stmt.else_branch)

    def _exec_for(self, stmt: ForStmt) -> None:
        loop_env = Environment(parent=self._current)
        prev = self._current
        self._current = loop_env
        try:
            if stmt.initializer:
                self._exec_stmt(stmt.initializer)
            while stmt.condition is None or self._is_truthy(self._eval(stmt.condition)):
                self._exec_stmt(stmt.body)
                if stmt.increment:
                    self._eval(stmt.increment)
        finally:
            self._current = prev

    def _exec_func_decl(self, stmt: FuncDeclStmt) -> None:
        self._current.define(stmt.name.origin, LangFunction(stmt, self._current))

    def _exec_return(self, stmt: ReturnStmt) -> None:
        value = self._eval(stmt.value) if stmt.value is not None else None
        raise ReturnSignal(value)

    def _exec_block(self, stmts: list[Stmt], env: Environment) -> None:
        prev = self._current
        try:
            self._current = env
            for stmt in stmts:
                self._exec_stmt(stmt)
        finally:
            self._current = prev

    # ── Expr 평가 ─────────────────────────────────────────
    def _eval(self, expr: Expr):
        handler = self._expr_handlers.get(type(expr))
        if handler:
            return handler(expr)
        raise LangRuntimeError(0, "알 수 없는 Expr 타입")

    def _eval_literal(self, expr: LiteralExpr):
        return expr.value

    def _eval_variable(self, expr: VariableExpr):
        distance = self._locals.get(id(expr))
        if distance is not None:
            return self._current.get_at(distance, expr.name.origin)
        return self._current.get(expr.name.origin, expr.name.line)

    def _eval_assign(self, expr: AssignExpr):
        val = self._eval(expr.value)
        distance = self._locals.get(id(expr))
        if distance is not None:
            self._current.assign_at(distance, expr.name.origin, val)
        else:
            self._current.assign(expr.name.origin, val, expr.name.line)
        return val

    def _eval_grouping(self, expr: GroupingExpr):
        return self._eval(expr.expression)

    def _eval_unary(self, expr: UnaryExpr):
        right = self._eval(expr.right)
        op = expr.operator.type
        if op == TokenType.MINUS:
            self._check_number(expr.operator, right)
            return -right
        if op == TokenType.BANG:
            return not self._is_truthy(right)

    def _eval_binary(self, expr: BinaryExpr):
        left = self._eval(expr.left)
        right = self._eval(expr.right)
        op = expr.operator.type
        line = expr.operator.line

        if op == TokenType.PLUS:
            if isinstance(left, float) and isinstance(right, float):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise LangRuntimeError(
                line, "피연산자는 반드시 숫자 또는 문자열이어야 합니다."
            )
        if op == TokenType.MINUS:
            self._check_numbers(expr.operator, left, right)
            return left - right
        if op == TokenType.STAR:
            self._check_numbers(expr.operator, left, right)
            return left * right
        if op == TokenType.SLASH:
            self._check_numbers(expr.operator, left, right)
            if right == 0:
                raise LangRuntimeError(line, "0으로 나눈 오류")
            return left / right
        if op == TokenType.GREATER:
            self._check_numbers(expr.operator, left, right)
            return left > right
        if op == TokenType.LESS:
            self._check_numbers(expr.operator, left, right)
            return left < right
        if op == TokenType.GREATER_EQUAL:
            self._check_numbers(expr.operator, left, right)
            return left >= right
        if op == TokenType.LESS_EQUAL:
            self._check_numbers(expr.operator, left, right)
            return left <= right
        if op == TokenType.EQUAL_EQUAL:
            return self._is_equal(left, right)
        if op == TokenType.BANG_EQUAL:
            return not self._is_equal(left, right)

    def _eval_call(self, expr: CallExpr):
        callee = self._eval(expr.callee)
        if not isinstance(callee, LangFunction):
            raise LangRuntimeError(expr.paren.line, "함수가 아닌 대상을 호출했습니다.")
        arguments = [self._eval(arg) for arg in expr.arguments]
        if len(arguments) != callee.arity:
            raise LangRuntimeError(expr.paren.line, "인자 개수가 일치하지 않습니다.")
        return callee.call(self, arguments)

    def _eval_logical(self, expr: LogicalExpr):
        left = self._eval(expr.left)
        if expr.operator.type == TokenType.OR:
            return left if self._is_truthy(left) else self._eval(expr.right)
        return self._eval(expr.right) if self._is_truthy(left) else left

    # ── 정적배열 기능 ─────────────────────────────────────
    def _eval_array(self, expr: ArrayExpr):
        size = self._eval(expr.size)
        self._check_array_size(expr.keyword, size)
        return [None] * int(size)

    def _eval_index_get(self, expr: IndexGetExpr):
        array = self._eval(expr.array)
        self._check_is_array(expr.bracket, array)
        index = self._check_index(expr.bracket, self._eval(expr.index), len(array))
        return array[index]

    def _eval_index_set(self, expr: IndexSetExpr):
        array = self._eval(expr.array)
        self._check_is_array(expr.bracket, array)
        index = self._check_index(expr.bracket, self._eval(expr.index), len(array))
        val = self._eval(expr.value)
        array[index] = val
        return val

    def _check_array_size(self, keyword, size) -> None:
        if not isinstance(size, float):
            raise LangRuntimeError(keyword.line, "배열의 크기는 숫자여야 합니다.")
        if size < 0 or size != int(size):
            raise LangRuntimeError(keyword.line, "배열의 크기는 0 이상의 정수여야 합니다.")

    def _check_is_array(self, bracket, val) -> None:
        if not isinstance(val, list):
            raise LangRuntimeError(bracket.line, "배열이 아닌 값에는 인덱스로 접근할 수 없습니다.")

    def _check_index(self, bracket, index, length: int) -> int:
        if not isinstance(index, float):
            raise LangRuntimeError(bracket.line, "배열 인덱스는 숫자여야 합니다.")
        if index != int(index):
            raise LangRuntimeError(bracket.line, "배열 인덱스는 정수여야 합니다.")
        i = int(index)
        if i < 0 or i >= length:
            raise LangRuntimeError(bracket.line, "배열 인덱스가 범위를 벗어났습니다.")
        return i

    # ── 헬퍼 ─────────────────────────────────────────────
    def _is_truthy(self, val) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        return True

    def _check_number(self, op, val) -> None:
        if not isinstance(val, float):
            raise LangRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _check_numbers(self, op, left, right) -> None:
        if not (isinstance(left, float) and isinstance(right, float)):
            raise LangRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _is_equal(self, left, right) -> bool:
        if type(left) is not type(right):
            return False
        return left == right

    def _stringify(self, val) -> str:
        if val is None:
            return "nil"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, float):
            s = str(val)
            return s[:-2] if s.endswith(".0") else s
        # 정적배열 기능: [10, 20, 30] 형태로 출력
        if isinstance(val, list):
            return "[" + ", ".join(self._stringify(v) for v in val) + "]"
        return str(val)
