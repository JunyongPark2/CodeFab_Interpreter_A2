from .ast_nodes import (
    AssignExpr,
    BinaryExpr,
    BlockStmt,
    Expr,
    ExpressionStmt,
    ForStmt,
    GroupingExpr,
    IfStmt,
    LogicalExpr,
    PrintStmt,
    Stmt,
    UnaryExpr,
    VarDeclStmt,
    VariableExpr,
)
from .errors import CheckError


class Checker:
    """AST를 DFS로 순회하며 의미 오류(중복 선언, 초기화식 자기 참조)를 검출한다."""

    def __init__(self, stmts: list[Stmt], global_scope: dict[str, bool] | None = None):
        self._stmts = stmts
        self._scopes: list[dict[str, bool]] = [
            global_scope if global_scope is not None else {}
        ]
        self._stmt_handlers = {
            VarDeclStmt: self._check_var_decl,
            BlockStmt: self._check_block,
            IfStmt: self._check_if,
            ForStmt: self._check_for,
            PrintStmt: lambda stmt: self._check_expr(stmt.expression),
            ExpressionStmt: lambda stmt: self._check_expr(stmt.expression),
        }
        self._expr_handlers = {
            VariableExpr: self._check_variable,
            AssignExpr: lambda expr: self._check_expr(expr.value),
            BinaryExpr: lambda expr: (
                self._check_expr(expr.left),
                self._check_expr(expr.right),
            ),
            UnaryExpr: lambda expr: self._check_expr(expr.right),
            GroupingExpr: lambda expr: self._check_expr(expr.expression),
            LogicalExpr: lambda expr: (
                self._check_expr(expr.left),
                self._check_expr(expr.right),
            ),
        }

    def check(self) -> None:
        for stmt in self._stmts:
            self._check_stmt(stmt)

    # ── Stmt 방문 ─────────────────────────────────────────
    def _check_stmt(self, stmt: Stmt) -> None:
        handler = self._stmt_handlers.get(type(stmt))
        if handler:
            handler(stmt)

    def _check_var_decl(self, stmt: VarDeclStmt) -> None:
        if self._current_scope is not None:
            self._declare(stmt.name.line, stmt.name.origin, self._current_scope)

        if stmt.initializer is not None:
            self._check_expr(stmt.initializer)

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
        self._check_expr(stmt.condition)
        self._check_stmt(stmt.then_branch)
        if stmt.else_branch:
            self._check_stmt(stmt.else_branch)

    def _check_for(self, stmt: ForStmt) -> None:
        self._begin_scope()
        if stmt.initializer:
            self._check_stmt(stmt.initializer)
        if stmt.condition:
            self._check_expr(stmt.condition)
        if stmt.increment:
            self._check_expr(stmt.increment)
        self._check_stmt(stmt.body)
        self._end_scope()

    # ── Expr 방문 ─────────────────────────────────────────
    def _check_expr(self, expr: Expr) -> None:
        handler = self._expr_handlers.get(type(expr))
        if handler:
            handler(expr)

    def _check_variable(self, expr: VariableExpr) -> None:
        scope = self._current_scope
        name = expr.name.origin
        if scope is not None and scope.get(name) is False:
            raise CheckError(
                expr.name.line, "자신의 초기화식에서 지역변수를 읽을 수 없습니다."
            )

    # ── 스코프 관리 ─────────────────────────────────────────
    @property
    def _current_scope(self) -> dict[str, bool] | None:
        return self._scopes[-1] if self._scopes else None

    def _begin_scope(self) -> None:
        self._scopes.append({})

    def _end_scope(self) -> None:
        self._scopes.pop()
