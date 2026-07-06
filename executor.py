from temp_implement import *
# executor.py
#from ast_nodes import * : Expr, Stmt
#from environment import Environment
from tokens import TokenType

class LangRuntimeError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")

class Executor:
    def __init__(self, stmts: list[Stmt]):
        self._stmts = stmts
        self._global  = Environment()
        self._current = self._global

    def execute(self) -> None:
        for stmt in self._stmts:
            self._exec_stmt(stmt)

    # ── Stmt 실행 ─────────────────────────────────────────
    def _exec_stmt(self, stmt: Stmt) -> None:
        if isinstance(stmt, PrintStmt):
            val = self._eval(stmt.expression)
            print(self._stringify(val))

        elif isinstance(stmt, VarDeclStmt):
            val = self._eval(stmt.initializer) if stmt.initializer else None
            self._current.define(stmt.name.origin, val)

        elif isinstance(stmt, ExpressionStmt):
            self._eval(stmt.expression)

        elif isinstance(stmt, BlockStmt):
            self._exec_block(stmt.statements, Environment(parent=self._current))

        elif isinstance(stmt, IfStmt):
            if self._is_truthy(self._eval(stmt.condition)):
                self._exec_stmt(stmt.then_branch)
            elif stmt.else_branch:
                self._exec_stmt(stmt.else_branch)

        elif isinstance(stmt, ForStmt):
            if stmt.initializer:
                self._exec_stmt(stmt.initializer)
            while stmt.condition is None or self._is_truthy(self._eval(stmt.condition)):
                self._exec_stmt(stmt.body)
                if stmt.increment:
                    self._eval(stmt.increment)

    def _exec_block(self, stmts: list[Stmt], env: Environment) -> None:
        prev = self._current
        try:
            self._current = env
            for stmt in stmts:
                self._exec_stmt(stmt)
        finally:
            self._current = prev   # 블록 종료 시 반드시 이전 환경 복귀

    # ── Expr 평가 ─────────────────────────────────────────
    def _eval(self, expr: Expr):
        if isinstance(expr, LiteralExpr):
            return expr.value

        if isinstance(expr, VariableExpr):
            return self._current.get(expr.name.origin)

        if isinstance(expr, AssignExpr):
            val = self._eval(expr.value)
            self._current.assign(expr.name.origin, val)
            return val

        if isinstance(expr, GroupingExpr):
            return self._eval(expr.expression)

        if isinstance(expr, UnaryExpr):
            right = self._eval(expr.right)
            op = expr.operator.type
            if op == TokenType.MINUS:
                self._check_number(expr.operator, right)
                return -right
            if op == TokenType.BANG:
                return not self._is_truthy(right)

        if isinstance(expr, BinaryExpr):
            left  = self._eval(expr.left)
            right = self._eval(expr.right)
            op    = expr.operator.type
            line  = expr.operator.line

            if op == TokenType.PLUS:
                if isinstance(left, float) and isinstance(right, float):
                    return left + right
                if isinstance(left, str) and isinstance(right, str):
                    return left + right
                raise LangRuntimeError(line, "피연산자는 반드시 숫자 또는 문자열이어야 합니다.")
            if op == TokenType.MINUS:
                self._check_numbers(expr.operator, left, right); return left - right
            if op == TokenType.STAR:
                self._check_numbers(expr.operator, left, right); return left * right
            if op == TokenType.SLASH:
                self._check_numbers(expr.operator, left, right)
                if right == 0:
                    raise LangRuntimeError(line, "0으로 나눈 오류")
                return left / right
            if op == TokenType.GREATER:
                self._check_numbers(expr.operator, left, right); return left > right
            if op == TokenType.LESS:
                self._check_numbers(expr.operator, left, right); return left < right

        if isinstance(expr, LogicalExpr):
            left = self._eval(expr.left)
            if expr.operator.type == TokenType.OR:
                return left if self._is_truthy(left) else self._eval(expr.right)
            # AND
            return self._eval(expr.right) if self._is_truthy(left) else left

        raise LangRuntimeError(0, "알 수 없는 Expr 타입")

    # ── 헬퍼 ─────────────────────────────────────────────
    def _is_truthy(self, val) -> bool:
        if val is None:        return False
        if isinstance(val, bool): return val
        return True   # 숫자, 문자열은 모두 truthy

    def _check_number(self, op, val) -> None:
        if not isinstance(val, float):
            raise LangRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _check_numbers(self, op, left, right) -> None:
        if not (isinstance(left, float) and isinstance(right, float)):
            raise LangRuntimeError(op.line, "피연산자는 반드시 숫자여야 합니다.")

    def _stringify(self, val) -> str:
        if val is None:   return "nil"
        if isinstance(val, bool): return "true" if val else "false"
        if isinstance(val, float):
            s = str(val)
            return s[:-2] if s.endswith(".0") else s
        return str(val)
    
