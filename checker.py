from ast_nodes import (
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


class CheckError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")


class Checker:
    def __init__(self, stmts: list[Stmt]):
        self._stmts = stmts
        self._scopes: list[dict[str, bool]] = []

    def check(self) -> None:
        for stmt in self._stmts:
            self._check_stmt(stmt)

    def _check_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, VarDeclStmt):
            self._check_var_decl(stmt)
        elif isinstance(stmt, BlockStmt):
            self._check_block(stmt)
        elif isinstance(stmt, IfStmt):
            self._check_if(stmt)
        elif isinstance(stmt, ForStmt):
            self._check_for(stmt)
        elif isinstance(stmt, PrintStmt):
            self._check_expr(stmt.expression)
        elif isinstance(stmt, ExpressionStmt):
            self._check_expr(stmt.expression)

    def _check_var_decl(self, stmt: VarDeclStmt) -> None:
        if self._scopes:
            scope = self._scopes[-1]
            if stmt.name.origin in scope:
                raise CheckError(
                    stmt.name.line,
                    f"변수 '{stmt.name.origin}'이(가) 이미 이 스코프에 선언되어 있습니다.",
                )
            scope[stmt.name.origin] = False

        if stmt.initializer is not None:
            self._check_expr(stmt.initializer)

        if self._scopes:
            self._scopes[-1][stmt.name.origin] = True

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

    def _check_expr(self, expr: Expr) -> None:
        if isinstance(expr, VariableExpr):
            name = expr.name.origin
            if self._scopes and name in self._scopes[-1] and not self._scopes[-1][name]:
                raise CheckError(expr.name.line, "자신의 초기화식에서 지역변수를 읽을 수 없습니다.")
        elif isinstance(expr, AssignExpr):
            self._check_expr(expr.value)
        elif isinstance(expr, BinaryExpr):
            self._check_expr(expr.left)
            self._check_expr(expr.right)
        elif isinstance(expr, UnaryExpr):
            self._check_expr(expr.right)
        elif isinstance(expr, GroupingExpr):
            self._check_expr(expr.expression)
        elif isinstance(expr, LogicalExpr):
            self._check_expr(expr.left)
            self._check_expr(expr.right)

    def _begin_scope(self) -> None:
        self._scopes.append({})

    def _end_scope(self) -> None:
        self._scopes.pop()
