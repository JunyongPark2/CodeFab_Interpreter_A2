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
from .errors import CheckError
from .tokens import TokenType

_NOT_FOLDABLE = object()


class Checker:
    """AST를 DFS로 순회하며 의미 오류(중복 선언, 초기화식 자기 참조)를 검출하고,
    실행 전 최적화(정적 바인딩 계산, 상수 폴딩)를 수행한다.

    최적화 때문에 Checker가 AST의 리터럴 하위 트리를 직접 치환할 수 있다
    (원래 "Checker는 AST를 수정하지 않는다"는 관례가 있었으나, 3일차 요구사항의
    상수 폴딩을 위해 이 범위 내에서 완화했다 — CodeFab_Interpreter_Guide.md 갱신 필요).
    """

    def __init__(self, stmts: list[Stmt], global_scope: dict[str, bool] | None = None):
        self._stmts = stmts
        self._scopes: list[dict[str, bool]] = [
            global_scope if global_scope is not None else {}
        ]
        # 변수 참조(VariableExpr)/대입(AssignExpr) 표현식마다 "몇 단계 위 스코프에
        # 있는지"를 기록한다. id(expr) -> distance. 못 찾으면(=전역) 기록하지 않는다.
        self._locals: dict[int, int] = {}
        # 현재 몇 겹의 함수 본문 안에 있는지 (함수 외부 return 검출용).
        self._function_depth = 0
        # 스코프별로 "이 스코프에서 새로 import된 파일 경로" 집합. self._scopes와 1:1로
        # push/pop된다 — 같은 파일이 현재 위치에서 "보이는" 스코프 체인 어딘가에 이미
        # import돼 있으면 재import를 막기 위함 (PDF 세부규칙 2: 상위 scope에서 이미
        # import된 파일은 하위에서 재import 불가, 단 스코프가 끝나면 그 기록도 사라짐).
        self._imported_paths: list[set[str]] = [set()]
        self._in_class = 0
        self._in_init = False
        self._in_super = 0  # 부모 클래스가 있는 클래스 본문 깊이

    def check(self) -> dict[int, int]:
        for stmt in self._stmts:
            stmt.accept(self)
        return self._locals

    # ── Stmt 방문 ─────────────────────────────────────────
    # (개별 visit_XxxStmt 메서드는 Stmt.accept()가 더블 디스패치로 직접 호출한다.
    # 새 Stmt 타입 추가 시 대응하는 visit_ 메서드가 없으면 accept()가 즉시
    # NotImplementedError를 낸다 — dict 디스패치 시절의 "조용한 누락"을 방지.)

    def visit_PrintStmt(self, stmt: PrintStmt) -> None:
        stmt.expression = self._check_expr(stmt.expression)

    def visit_ExpressionStmt(self, stmt: ExpressionStmt) -> None:
        stmt.expression = self._check_expr(stmt.expression)

    def visit_VarDeclStmt(self, stmt: VarDeclStmt) -> None:
        if self._current_scope is not None:
            self._declare(stmt.name.line, stmt.name.origin, self._current_scope)

        if stmt.initializer is not None:
            stmt.initializer = self._check_expr(stmt.initializer)

        if self._current_scope is not None:
            self._current_scope[stmt.name.origin] = True

    def _declare(self, line: int, name: str, scope: dict[str, bool]) -> None:
        if name in scope:
            raise CheckError(
                line, f"변수 '{name}'이(가) 이미 이 스코프에 선언되어 있습니다."
            )
        scope[name] = False

    def visit_BlockStmt(self, stmt: BlockStmt) -> None:
        self._begin_scope()
        for s in stmt.statements:
            s.accept(self)
        self._end_scope()

    def visit_IfStmt(self, stmt: IfStmt) -> None:
        stmt.condition = self._check_expr(stmt.condition)
        stmt.then_branch.accept(self)
        if stmt.else_branch:
            stmt.else_branch.accept(self)

    def visit_ForStmt(self, stmt: ForStmt) -> None:
        self._begin_scope()
        if stmt.initializer:
            stmt.initializer.accept(self)
        if stmt.condition:
            stmt.condition = self._check_expr(stmt.condition)
        if stmt.increment:
            stmt.increment = self._check_expr(stmt.increment)
        stmt.body.accept(self)
        self._end_scope()

    def visit_FuncDeclStmt(self, stmt: FuncDeclStmt, is_init: bool = False) -> None:
        if self._current_scope is not None:
            self._declare(stmt.name.line, stmt.name.origin, self._current_scope)
            # 재귀 호출을 위해 본문을 검사하기 전에 즉시 정의 완료로 표시한다
            # (var 선언과 달리 "자기 자신을 참조하는 초기화식" 제약이 없다).
            self._current_scope[stmt.name.origin] = True

        self._check_duplicate_params(stmt.params)

        prev_in_init = self._in_init
        self._in_init = is_init
        self._function_depth += 1
        self._begin_scope()
        for param in stmt.params:
            self._current_scope[param.origin] = (
                True  # 파라미터는 이미 초기화된 것으로 취급
            )
        for body_stmt in stmt.body:
            body_stmt.accept(self)
        self._end_scope()
        self._function_depth -= 1
        self._in_init = prev_in_init

    def _check_duplicate_params(self, params: list) -> None:
        seen: set[str] = set()
        for param in params:
            if param.origin in seen:
                raise CheckError(
                    param.line, f"파라미터 이름 '{param.origin}'이(가) 중복되었습니다."
                )
            seen.add(param.origin)

    def visit_ReturnStmt(self, stmt: ReturnStmt) -> None:
        if self._function_depth == 0:
            raise CheckError(
                stmt.keyword.line, "함수 외부에서는 return을 사용할 수 없습니다."
            )
        if self._in_init and stmt.value is not None:
            raise CheckError(
                stmt.keyword.line, "init 메서드는 값을 반환할 수 없습니다."
            )
        if stmt.value is not None:
            stmt.value = self._check_expr(stmt.value)

    def visit_ImportStmt(self, stmt: ImportStmt) -> None:
        path = stmt.path.value
        for scope_paths in self._imported_paths:
            if path in scope_paths:
                raise CheckError(stmt.path.line, f"이미 import된 파일입니다: '{path}'")
        self._imported_paths[-1].add(path)

        # alias도 var/함수 선언처럼 현재 스코프에 등록되는 이름으로 취급한다
        # (같은 스코프 안에서 alias 이름이 변수/함수와 충돌하면 CheckError).
        if self._current_scope is not None:
            self._declare(stmt.alias.line, stmt.alias.origin, self._current_scope)
            self._current_scope[stmt.alias.origin] = True

    def visit_ClassDeclStmt(self, stmt: ClassDeclStmt) -> None:
        if (
            stmt.superclass is not None
            and stmt.superclass.name.origin == stmt.name.origin
        ):
            raise CheckError(stmt.name.line, "클래스는 자기 자신을 상속할 수 없습니다.")

        self._in_class += 1

        if stmt.superclass is not None:
            self._check_expr(stmt.superclass)
            self._begin_scope()
            self._current_scope["Super"] = True
            self._in_super += 1

        self._begin_scope()
        self._current_scope["This"] = True
        for method in stmt.methods:
            self.visit_FuncDeclStmt(method, is_init=(method.name.origin == "init"))
        self._end_scope()

        if stmt.superclass is not None:
            self._end_scope()
            self._in_super -= 1

        self._in_class -= 1

    # ── Expr 방문 (검사 + 최적화) ────────────────────────────
    # (개별 visit_XxxExpr 메서드는 Expr.accept()가 더블 디스패치로 직접 호출한다.)
    def _check_expr(self, expr: Expr) -> Expr:
        """expr을 검사하고, 상수로 접을 수 있으면 접은 결과를 돌려준다.
        호출부는 반환값을 원래 필드에 다시 대입해야 트리 교체가 반영된다."""
        expr.accept(self)
        return self._fold(expr)

    def visit_LiteralExpr(self, expr: LiteralExpr) -> None:
        pass  # 리터럴은 검사할 게 없다 — exhaustiveness를 위해 명시적으로 no-op 처리.

    def visit_VariableExpr(self, expr: VariableExpr) -> None:
        scope = self._current_scope
        name = expr.name.origin
        if scope is not None and scope.get(name) is False:
            raise CheckError(
                expr.name.line, "자신의 초기화식에서 지역변수를 읽을 수 없습니다."
            )
        self._resolve_local(expr, name)

    def visit_AssignExpr(self, expr: AssignExpr) -> None:
        expr.value = self._check_expr(expr.value)
        self._resolve_local(expr, expr.name.origin)

    def visit_BinaryExpr(self, expr: BinaryExpr) -> None:
        expr.left = self._check_expr(expr.left)
        expr.right = self._check_expr(expr.right)

    def visit_UnaryExpr(self, expr: UnaryExpr) -> None:
        expr.right = self._check_expr(expr.right)

    def visit_GroupingExpr(self, expr: GroupingExpr) -> None:
        expr.expression = self._check_expr(expr.expression)

    def visit_LogicalExpr(self, expr: LogicalExpr) -> None:
        expr.left = self._check_expr(expr.left)
        expr.right = self._check_expr(expr.right)

    def visit_ArrayExpr(self, expr: ArrayExpr) -> None:
        expr.size = self._check_expr(expr.size)

    def visit_IndexGetExpr(self, expr: IndexGetExpr) -> None:
        expr.array = self._check_expr(expr.array)
        expr.index = self._check_expr(expr.index)

    def visit_IndexSetExpr(self, expr: IndexSetExpr) -> None:
        expr.array = self._check_expr(expr.array)
        expr.index = self._check_expr(expr.index)
        expr.value = self._check_expr(expr.value)

    def visit_CallExpr(self, expr: CallExpr) -> None:
        expr.callee = self._check_expr(expr.callee)
        expr.arguments = [self._check_expr(arg) for arg in expr.arguments]

    def visit_GetExpr(self, expr: GetExpr) -> None:
        # 기존 동작 유지: object의 폴딩 결과는 반영하지 않는다(에러 검출/바인딩만 목적).
        self._check_expr(expr.object)

    def visit_SetExpr(self, expr: SetExpr) -> None:
        self._check_expr(expr.object)
        self._check_expr(expr.value)

    def visit_ThisExpr(self, expr: ThisExpr) -> None:
        if self._in_class == 0:
            raise CheckError(
                expr.keyword.line, "클래스 외부에서 'This'를 사용할 수 없습니다."
            )
        # Super와 동일하게 정적 바인딩 대상이다. This는 CodeFabFunction.bind()가
        # 메서드 호출마다 정확히 스코프 1개(This를 담은 Environment)를 새로 만드는
        # 구조라, Checker가 계산하는 distance와 런타임 스코프 깊이가 항상 일치한다.
        self._resolve_local(expr, "This")

    def visit_SuperExpr(self, expr: SuperExpr) -> None:
        if self._in_class == 0:
            raise CheckError(
                expr.keyword.line, "클래스 외부에서 'Super'를 사용할 수 없습니다."
            )
        if self._in_super == 0:
            raise CheckError(
                expr.keyword.line,
                "부모 클래스가 없는 클래스에서 'Super'를 사용할 수 없습니다.",
            )
        self._resolve_local(expr, "Super")

    def visit_InstanceOfExpr(self, expr: InstanceOfExpr) -> None:
        # 기존 동작 유지: object의 폴딩 결과는 반영하지 않는다(에러 검출/바인딩만 목적).
        self._check_expr(expr.object)

    # ── 실행 전 최적화: 정적 바인딩 ────────────────────────────
    def _resolve_local(self, expr: Expr, name: str) -> None:
        # self._scopes[0]은 이번 run() 이전에 이미 선언된 전역 스코프이므로 제외한다
        # (최상위/REPL 전역 변수는 건드리지 않고 Executor의 기존 동적 조회를 그대로 쓴다).
        local_scopes = self._scopes[1:]
        for distance, scope in enumerate(reversed(local_scopes)):
            if name in scope:
                self._locals[id(expr)] = distance
                return
        # 못 찾으면 전역 변수 — distance 기록 안 함

    # ── 실행 전 최적화: 상수 폴딩 ────────────────────────────
    def _fold(self, expr: Expr) -> Expr:
        """expr의 자식들은 이미 _check_expr()에서 검사·폴딩까지 끝난 상태다.
        여기서는 expr 자신이 리터럴로 접힐 수 있는지만 판단한다."""
        if isinstance(expr, GroupingExpr) and isinstance(expr.expression, LiteralExpr):
            return expr.expression

        if isinstance(expr, UnaryExpr) and isinstance(expr.right, LiteralExpr):
            if expr.operator.type == TokenType.MINUS and isinstance(
                expr.right.value, float
            ):
                return LiteralExpr(-expr.right.value)
            if expr.operator.type == TokenType.BANG:
                return LiteralExpr(not self._is_truthy(expr.right.value))

        if (
            isinstance(expr, BinaryExpr)
            and isinstance(expr.left, LiteralExpr)
            and isinstance(expr.right, LiteralExpr)
        ):
            folded = self._try_fold_binary(
                expr.operator, expr.left.value, expr.right.value
            )
            if folded is not _NOT_FOLDABLE:
                return LiteralExpr(folded)

        return expr

    def _try_fold_binary(self, operator, left, right):
        """계산이 실패할 수 있는 경우(타입 불일치, 0으로 나누기)는 접지 않고
        _NOT_FOLDABLE을 반환한다 — Executor가 평소처럼 런타임 에러를 내게 하기 위함.
        Executor._eval_binary와 동일한 의미론을 유지해야 한다 (한쪽만 바뀌면
        폴딩된 코드와 안 된 코드의 동작이 달라질 수 있으니 함께 수정할 것)."""
        op = operator.type
        numbers = isinstance(left, float) and isinstance(right, float)
        try:
            if op == TokenType.PLUS:
                if numbers or (isinstance(left, str) and isinstance(right, str)):
                    return left + right
                return _NOT_FOLDABLE
            if op == TokenType.MINUS:
                return left - right if numbers else _NOT_FOLDABLE
            if op == TokenType.STAR:
                return left * right if numbers else _NOT_FOLDABLE
            if op == TokenType.SLASH:
                if not numbers or right == 0:
                    return _NOT_FOLDABLE
                return left / right
            if op == TokenType.GREATER:
                return left > right if numbers else _NOT_FOLDABLE
            if op == TokenType.LESS:
                return left < right if numbers else _NOT_FOLDABLE
            if op == TokenType.GREATER_EQUAL:
                return left >= right if numbers else _NOT_FOLDABLE
            if op == TokenType.LESS_EQUAL:
                return left <= right if numbers else _NOT_FOLDABLE
            if op == TokenType.EQUAL_EQUAL:
                return type(left) is type(right) and left == right
            if op == TokenType.BANG_EQUAL:
                return not (type(left) is type(right) and left == right)
        except (TypeError, ZeroDivisionError):
            return _NOT_FOLDABLE
        return _NOT_FOLDABLE

    def _is_truthy(self, val) -> bool:
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        return True

    # ── 스코프 관리 ─────────────────────────────────────────
    @property
    def _current_scope(self) -> dict[str, bool] | None:
        return self._scopes[-1] if self._scopes else None

    def _begin_scope(self) -> None:
        self._scopes.append({})
        self._imported_paths.append(set())

    def _end_scope(self) -> None:
        self._scopes.pop()
        self._imported_paths.pop()
