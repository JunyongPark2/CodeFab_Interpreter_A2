from .ast_nodes import (
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
    LiteralExpr,
    LogicalExpr,
    PrintStmt,
    ReturnStmt,
    Stmt,
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

        self._stmt_handlers = {
            VarDeclStmt: self._check_var_decl,
            BlockStmt: self._check_block,
            IfStmt: self._check_if,
            ForStmt: self._check_for,
            PrintStmt: self._check_print,
            ExpressionStmt: self._check_expression_stmt,
            FuncDeclStmt: self._check_func_decl,
            ReturnStmt: self._check_return,
        }
        self._expr_handlers = {
            VariableExpr: self._check_variable,
            AssignExpr: self._check_assign,
            BinaryExpr: self._check_binary,
            UnaryExpr: self._check_unary,
            GroupingExpr: self._check_grouping,
            LogicalExpr: self._check_logical,
            CallExpr: self._check_call,
        }

    def check(self) -> dict[int, int]:
        for stmt in self._stmts:
            self._check_stmt(stmt)
        return self._locals

    # ── Stmt 방문 ─────────────────────────────────────────
    def _check_stmt(self, stmt: Stmt) -> None:
        handler = self._stmt_handlers.get(type(stmt))
        if handler:
            handler(stmt)

    def _check_print(self, stmt: PrintStmt) -> None:
        stmt.expression = self._check_expr(stmt.expression)

    def _check_expression_stmt(self, stmt: ExpressionStmt) -> None:
        stmt.expression = self._check_expr(stmt.expression)

    def _check_var_decl(self, stmt: VarDeclStmt) -> None:
        if self._current_scope is not None:
            self._declare(stmt.name.line, stmt.name.origin, self._current_scope)

        if stmt.initializer is not None:
            stmt.initializer = self._check_expr(stmt.initializer)

        if self._current_scope is not None:
            self._current_scope[stmt.name.origin] = True  # 초기화 완료

    def _declare(self, line: int, name: str, scope: dict[str, bool]) -> None:
        if name in scope:
            raise CheckError(
                line, f"변수 '{name}'이(가) 이미 이 스코프에 선언되어 있습니다."
            )
        scope[name] = False  # 초기화 미완

    def _check_block(self, stmt: BlockStmt) -> None:
        self._begin_scope()
        for s in stmt.statements:
            self._check_stmt(s)
        self._end_scope()

    def _check_if(self, stmt: IfStmt) -> None:
        stmt.condition = self._check_expr(stmt.condition)
        self._check_stmt(stmt.then_branch)
        if stmt.else_branch:
            self._check_stmt(stmt.else_branch)

    def _check_for(self, stmt: ForStmt) -> None:
        self._begin_scope()
        if stmt.initializer:
            self._check_stmt(stmt.initializer)
        if stmt.condition:
            stmt.condition = self._check_expr(stmt.condition)
        if stmt.increment:
            stmt.increment = self._check_expr(stmt.increment)
        self._check_stmt(stmt.body)
        self._end_scope()

    def _check_func_decl(self, stmt: FuncDeclStmt) -> None:
        if self._current_scope is not None:
            self._declare(stmt.name.line, stmt.name.origin, self._current_scope)
            # 재귀 호출을 위해 본문을 검사하기 전에 즉시 정의 완료로 표시한다
            # (var 선언과 달리 "자기 자신을 참조하는 초기화식" 제약이 없다).
            self._current_scope[stmt.name.origin] = True

        self._check_duplicate_params(stmt.params)

        self._function_depth += 1
        self._begin_scope()
        for param in stmt.params:
            self._current_scope[param.origin] = True  # 파라미터는 이미 초기화된 것으로 취급
        for body_stmt in stmt.body:
            self._check_stmt(body_stmt)
        self._end_scope()
        self._function_depth -= 1

    def _check_duplicate_params(self, params: list) -> None:
        seen: set[str] = set()
        for param in params:
            if param.origin in seen:
                raise CheckError(
                    param.line, f"파라미터 이름 '{param.origin}'이(가) 중복되었습니다."
                )
            seen.add(param.origin)

    def _check_return(self, stmt: ReturnStmt) -> None:
        if self._function_depth == 0:
            raise CheckError(
                stmt.keyword.line, "함수 외부에서는 return을 사용할 수 없습니다."
            )
        if stmt.value is not None:
            stmt.value = self._check_expr(stmt.value)

    # ── Expr 방문 (검사 + 최적화) ────────────────────────────
    def _check_expr(self, expr: Expr) -> Expr:
        """expr을 검사하고, 상수로 접을 수 있으면 접은 결과를 돌려준다.
        호출부는 반환값을 원래 필드에 다시 대입해야 트리 교체가 반영된다."""
        handler = self._expr_handlers.get(type(expr))
        if handler:
            handler(expr)
        return self._fold(expr)

    def _check_variable(self, expr: VariableExpr) -> None:
        scope = self._current_scope
        name = expr.name.origin
        if scope is not None and scope.get(name) is False:
            raise CheckError(
                expr.name.line, "자신의 초기화식에서 지역변수를 읽을 수 없습니다."
            )
        self._resolve_local(expr, name)

    def _check_assign(self, expr: AssignExpr) -> None:
        expr.value = self._check_expr(expr.value)
        self._resolve_local(expr, expr.name.origin)

    def _check_binary(self, expr: BinaryExpr) -> None:
        expr.left = self._check_expr(expr.left)
        expr.right = self._check_expr(expr.right)

    def _check_unary(self, expr: UnaryExpr) -> None:
        expr.right = self._check_expr(expr.right)

    def _check_grouping(self, expr: GroupingExpr) -> None:
        expr.expression = self._check_expr(expr.expression)

    def _check_logical(self, expr: LogicalExpr) -> None:
        expr.left = self._check_expr(expr.left)
        expr.right = self._check_expr(expr.right)

    def _check_call(self, expr: CallExpr) -> None:
        expr.callee = self._check_expr(expr.callee)
        expr.arguments = [self._check_expr(arg) for arg in expr.arguments]

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

    def _end_scope(self) -> None:
        self._scopes.pop()
