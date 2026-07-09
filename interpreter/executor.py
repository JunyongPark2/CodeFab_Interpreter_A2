from __future__ import annotations

from typing import Callable, Optional

from .ast_nodes import (
    ArrayExpr,
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    CallExpr,
    ClassDeclStmt,
    Expr,
    ExpressionStmt,
    ForStmt,
    FuncDeclStmt,
    GetExpr,
    GroupingExpr,
    IfStmt,
    ImportStmt,
    IndexGetExpr,
    IndexSetExpr,
    InstanceOfExpr,
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    ReturnStmt,
    SetExpr,
    Stmt,
    SuperExpr,
    ThisExpr,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from .checker import Checker
from .environment import Environment
from .errors import CodeFabRuntimeError
from .loader import Loader
from .runtime import (
    CodeFabCallable,
    CodeFabClass,
    CodeFabFunction,
    CodeFabInstance,
    CodeFabModule,
    _ReturnSignal,
)
from .tokens import TokenType


class Executor:
    def __init__(
        self,
        stmts: list[Stmt],
        environment: Environment | None = None,
        locals: dict[int, int] | None = None,
        loader: Loader | None = None,
        on_stmt: Optional[Callable[[Stmt, int, "Executor"], None]] = None,
        source: str = "",
        path: str = "<main>",
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
        # import 실행에 쓰는 파일 로더. None이면(예: 손으로 AST를 만든 단위테스트)
        # ImportStmt를 만나도 실행할 수 없다는 명확한 에러를 낸다.
        self._loader = loader
        # 디버그 모드(factory_shell debug)가 Stmt 단위 stepping을 구현하는 데 쓰는 훅.
        # (stmt, depth, self)로 호출되며, depth는 현재 몇 겹의 블록 안인지를 나타낸다
        # (0=최상위) — "next"가 블록 내부로 진입하지 않고 건너뛰는 데 필요하다.
        self._on_stmt = on_stmt
        self._depth = 0
        # 디버그 모드가 on_stmt에서 "이 Stmt는 어느 파일 몇 번째 줄인가"를 보여줄 때 쓴다.
        # import된 모듈은 자기 자신의 소스/경로를 갖고 있어야 하므로(_exec_import 참고),
        # Executor 인스턴스마다 자신이 실행 중인 파일의 소스와 경로를 따로 들고 있는다.
        self._source_lines = source.splitlines()
        self._path = path

    def execute(self) -> None:
        for stmt in self._stmts:
            self._exec_stmt(stmt)

    @property
    def current_env(self) -> Environment:
        """디버그 모드가 watch/inspect 구현 시 현재 실행 스코프를 들여다보는 용도."""
        return self._current

    @property
    def source_lines(self) -> list[str]:
        """디버그 모드가 on_stmt에서 현재 실행 중인 파일의 소스 줄을 보여주는 용도."""
        return self._source_lines

    @property
    def path(self) -> str:
        """디버그 모드가 on_stmt에서 현재 실행 중인 파일 경로를 보여주는 용도."""
        return self._path

    # ── Stmt 실행 ─────────────────────────────────────────
    # (개별 visit_XxxStmt 메서드는 Stmt.accept()가 더블 디스패치로 직접 호출한다.
    # 새 Stmt 타입 추가 시 대응하는 visit_ 메서드가 없으면 accept()가 즉시
    # NotImplementedError를 낸다 — dict 디스패치 시절의 "조용한 누락"을 방지.
    # 단, Stmt는 실행 전에 디버그 모드의 on_stmt 훅을 반드시 거쳐야 하므로
    # (Expr와 달리) stmt.accept(self)를 직접 부르지 않고 항상 _exec_stmt()를
    # 통해서만 실행한다 — 아래 execute()/visit_IfStmt/visit_ForStmt/_exec_block 참고.)

    def _exec_stmt(self, stmt: Stmt) -> None:
        if self._on_stmt is not None:
            self._on_stmt(stmt, self._depth, self)
        stmt.accept(self)

    def visit_PrintStmt(self, stmt: PrintStmt) -> None:
        print(self._stringify(self._eval(stmt.expression)))

    def visit_VarDeclStmt(self, stmt: VarDeclStmt) -> None:
        val = self._eval(stmt.initializer) if stmt.initializer else None
        self._current.define(stmt.name.origin, val)

    def visit_ExpressionStmt(self, stmt: ExpressionStmt) -> None:
        self._eval(stmt.expression)

    def visit_BlockStmt(self, stmt: BlockStmt) -> None:
        self._exec_block(stmt.statements, Environment(parent=self._current))

    def visit_IfStmt(self, stmt: IfStmt) -> None:
        if self._is_truthy(self._eval(stmt.condition)):
            self._exec_stmt(stmt.then_branch)
        elif stmt.else_branch:
            self._exec_stmt(stmt.else_branch)

    def visit_ForStmt(self, stmt: ForStmt) -> None:
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

    def visit_FuncDeclStmt(self, stmt: FuncDeclStmt) -> None:
        func = CodeFabFunction(stmt, self._current)
        self._current.define(stmt.name.origin, func)

    def visit_ReturnStmt(self, stmt: ReturnStmt) -> None:
        value = self._eval(stmt.value) if stmt.value is not None else None
        raise _ReturnSignal(value)

    def visit_ClassDeclStmt(self, stmt: ClassDeclStmt) -> None:
        superclass = None
        if stmt.superclass is not None:
            superclass = self._eval(stmt.superclass)
            if not isinstance(superclass, CodeFabClass):
                raise CodeFabRuntimeError(
                    stmt.superclass.name.line, "부모 클래스는 클래스여야 합니다."
                )

        self._current.define(stmt.name.origin, None)

        if stmt.superclass is not None:
            env = Environment(parent=self._current)
            env.define("Super", superclass)
            self._current = env

        methods: dict[str, CodeFabFunction] = {}
        for method in stmt.methods:
            is_init = method.name.origin == "init"
            func = CodeFabFunction(method, self._current, is_init)
            methods[method.name.origin] = func

        klass = CodeFabClass(stmt.name.origin, superclass, methods)

        if stmt.superclass is not None:
            self._current = self._current.parent  # type: ignore[assignment]

        self._current.assign(stmt.name.origin, klass, stmt.name.line)

    def visit_ImportStmt(self, stmt: ImportStmt) -> None:
        if self._loader is None:
            raise CodeFabRuntimeError(
                stmt.path.line, "이 실행 환경에서는 import를 사용할 수 없습니다."
            )
        path = stmt.path.value
        # 순환 import 탐지 구간은 "이 파일을 로드하고 실행하는 동안 전체"여야 한다.
        # 실행 중에 이 파일을 다시 import하려는 시도까지 잡아내야 하기 때문.
        with self._loader.loading(path, stmt.path.line):
            stmts = self._loader.load(path, stmt.path.line)
            # 디버그 모드가 module 내부에서 멈출 때 올바른 파일의 소스 줄을 보여줄 수
            # 있도록, module 자신의 소스도 함께 읽어 nested Executor에 넘긴다.
            with open(path, encoding="utf-8") as f:
                module_source = f.read()

            # import된 파일은 독립된 네임스페이스(부모 없는 Environment)에서 실행한다 —
            # 현재 실행 중인 스코프의 변수를 보거나 건드리면 안 되기 때문.
            module_locals = Checker(stmts).check()
            module_env = Environment()
            Executor(
                stmts,
                environment=module_env,
                locals=module_locals,
                loader=self._loader,
                on_stmt=self._on_stmt,
                source=module_source,
                path=path,
            ).execute()

        module = CodeFabModule(stmt.alias.origin)
        module.fields.update(module_env.snapshot())
        self._current.define(stmt.alias.origin, module)

    def _exec_block(self, stmts: list[Stmt], env: Environment) -> None:
        """블록 진입 시 스코프를 바꿔 문장을 순차 실행하는 공용 헬퍼.
        visit_BlockStmt뿐 아니라 함수/메서드 호출(CodeFabFunction.call)도 재사용한다.
        stmt.accept(self)를 직접 부르지 않고 _exec_stmt()를 거쳐야, 블록/함수 본문
        안의 문장에서도 디버그 모드의 on_stmt 훅이 빠짐없이 호출된다."""
        prev = self._current
        self._depth += 1
        try:
            self._current = env
            for stmt in stmts:
                self._exec_stmt(stmt)
        finally:
            self._current = prev
            self._depth -= 1

    # ── Expr 평가 ─────────────────────────────────────────
    # (개별 visit_XxxExpr 메서드는 Expr.accept()가 더블 디스패치로 직접 호출한다.)
    def _eval(self, expr: Expr):
        return expr.accept(self)

    def visit_LiteralExpr(self, expr: LiteralExpr):
        return expr.value

    def visit_VariableExpr(self, expr: VariableExpr):
        distance = self._locals.get(id(expr))
        if distance is not None:
            return self._current.get_at(distance, expr.name.origin)
        return self._current.get(expr.name.origin, expr.name.line)

    def visit_AssignExpr(self, expr: AssignExpr):
        val = self._eval(expr.value)
        distance = self._locals.get(id(expr))
        if distance is not None:
            self._current.assign_at(distance, expr.name.origin, val)
        else:
            self._current.assign(expr.name.origin, val, expr.name.line)
        return val

    def visit_GroupingExpr(self, expr: GroupingExpr):
        return self._eval(expr.expression)

    def visit_UnaryExpr(self, expr: UnaryExpr):
        right = self._eval(expr.right)
        op = expr.operator.type
        if op == TokenType.MINUS:
            self._check_number(expr.operator, right)
            return -right
        if op == TokenType.BANG:
            return not self._is_truthy(right)

    def visit_BinaryExpr(self, expr: BinaryExpr):
        left = self._eval(expr.left)
        right = self._eval(expr.right)
        op = expr.operator.type
        line = expr.operator.line

        if op == TokenType.PLUS:
            if isinstance(left, float) and isinstance(right, float):
                return left + right
            if isinstance(left, str) and isinstance(right, str):
                return left + right
            raise CodeFabRuntimeError(
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
                raise CodeFabRuntimeError(line, "0으로 나눈 오류")
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

    def visit_LogicalExpr(self, expr: LogicalExpr):
        left = self._eval(expr.left)
        if expr.operator.type == TokenType.OR:
            return left if self._is_truthy(left) else self._eval(expr.right)
        return self._eval(expr.right) if self._is_truthy(left) else left

    # ── 정적배열 기능 ─────────────────────────────────────
    def visit_ArrayExpr(self, expr: ArrayExpr):
        size = self._eval(expr.size)
        self._check_array_size(expr.keyword, size)
        return [None] * int(size)

    def visit_IndexGetExpr(self, expr: IndexGetExpr):
        array = self._eval(expr.array)
        self._check_is_array(expr.bracket, array)
        index = self._check_index(expr.bracket, self._eval(expr.index), len(array))
        return array[index]

    def visit_IndexSetExpr(self, expr: IndexSetExpr):
        array = self._eval(expr.array)
        self._check_is_array(expr.bracket, array)
        index = self._check_index(expr.bracket, self._eval(expr.index), len(array))
        val = self._eval(expr.value)
        array[index] = val
        return val

    def _check_array_size(self, keyword, size) -> None:
        if not isinstance(size, float):
            raise CodeFabRuntimeError(keyword.line, "배열의 크기는 숫자여야 합니다.")
        if size < 0 or size != int(size):
            raise CodeFabRuntimeError(
                keyword.line, "배열의 크기는 0 이상의 정수여야 합니다."
            )

    def _check_is_array(self, bracket, val) -> None:
        if not isinstance(val, list):
            raise CodeFabRuntimeError(
                bracket.line, "배열이 아닌 값에는 인덱스로 접근할 수 없습니다."
            )

    def _check_index(self, bracket, index, length: int) -> int:
        if not isinstance(index, float):
            raise CodeFabRuntimeError(bracket.line, "배열 인덱스는 숫자여야 합니다.")
        if index != int(index):
            raise CodeFabRuntimeError(bracket.line, "배열 인덱스는 정수여야 합니다.")
        i = int(index)
        if i < 0 or i >= length:
            raise CodeFabRuntimeError(
                bracket.line, "배열 인덱스가 범위를 벗어났습니다."
            )
        return i

    def visit_CallExpr(self, expr: CallExpr):
        callee = self._eval(expr.callee)
        arguments = [self._eval(arg) for arg in expr.arguments]

        if not isinstance(callee, CodeFabCallable):
            raise CodeFabRuntimeError(
                expr.paren.line, "함수가 아닌 대상을 호출했습니다."
            )

        if len(arguments) != callee.arity():
            raise CodeFabRuntimeError(expr.paren.line, "인자 개수가 일치하지 않습니다.")

        return callee.call(self, arguments)

    def visit_GetExpr(self, expr: GetExpr):
        obj = self._eval(expr.object)
        if isinstance(obj, CodeFabModule):
            # import된 모듈의 멤버 접근: sum.add, sum.VERSION 등.
            # CodeFabModule.get()은 CodeFabInstance.get()과 달리 Token이 아니라
            # (str, line)을 받으므로 여기서 풀어서 넘긴다.
            return obj.get(expr.name.origin, expr.name.line)
        if not isinstance(obj, CodeFabInstance):
            raise CodeFabRuntimeError(
                expr.name.line, "인스턴스에서만 속성에 접근할 수 있습니다."
            )
        return obj.get(expr.name)

    def visit_SetExpr(self, expr: SetExpr):
        obj = self._eval(expr.object)
        if isinstance(obj, CodeFabModule):
            # import된 모듈은 읽기 전용 네임스페이스로 취급한다 (sum.x = 1; 금지).
            raise CodeFabRuntimeError(
                expr.name.line, "모듈에는 값을 대입할 수 없습니다."
            )
        if not isinstance(obj, CodeFabInstance):
            raise CodeFabRuntimeError(
                expr.name.line, "인스턴스에서만 속성에 접근할 수 있습니다."
            )
        value = self._eval(expr.value)
        obj.set(expr.name, value)
        return value

    def visit_ThisExpr(self, expr: ThisExpr):
        distance = self._locals.get(id(expr))
        if distance is not None:
            return self._current.get_at(distance, "This")
        return self._current.get("This", expr.keyword.line)

    def visit_SuperExpr(self, expr: SuperExpr):
        distance = self._locals.get(id(expr))
        if distance is not None:
            superclass = self._current.get_at(distance, "Super")
            instance = self._current.get_at(distance - 1, "This")
        else:
            superclass = self._current.get("Super", expr.keyword.line)
            instance = self._current.get("This", expr.keyword.line)
        method = superclass.find_method(expr.method.origin)
        if method is None:
            raise CodeFabRuntimeError(
                expr.method.line, f"'{expr.method.origin}' 메서드가 존재하지 않습니다."
            )
        return method.bind(instance)

    def visit_InstanceOfExpr(self, expr: InstanceOfExpr):
        obj = self._eval(expr.object)
        if not isinstance(obj, CodeFabInstance):
            return False
        klass = obj.klass
        while klass is not None:
            if klass.name == expr.klass.origin:
                return True
            klass = klass.superclass
        return False

    # ── 헬퍼 ─────────────────────────────────────────────
    def _is_truthy(self, val) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        return True

    def _check_number(self, op, val) -> None:
        if not isinstance(val, float):
            raise CodeFabRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _check_numbers(self, op, left, right) -> None:
        if not (isinstance(left, float) and isinstance(right, float)):
            raise CodeFabRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _is_equal(self, left, right) -> bool:
        if type(left) is not type(right):
            return False
        return left == right

    def _stringify(self, val) -> str:
        if val is None:
            return "null"
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, float):
            s = str(val)
            return s[:-2] if s.endswith(".0") else s
        # 정적배열 기능: [10, 20, 30] 형태로 출력
        if isinstance(val, list):
            return "[" + ", ".join(self._stringify(v) for v in val) + "]"
        return str(val)
