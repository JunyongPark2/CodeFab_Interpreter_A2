from __future__ import annotations

# prompt_shell.py의 REPL 종료 명령어와 동일하게 맞춘다 (exit/quit 표기를 셸마다
# 다르게 두지 않기 위해 같은 집합을 그대로 가져다 쓴다).
from prompt_shell import EXIT_COMMANDS

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
from .errors import CodeFabRuntimeError


class DebugExit(Exception):
    """디버그 세션에서 `exit`/`quit`을 입력해 남은 실행을 중단했을 때 던진다.

    Executor.execute() 내부 깊숙이(재귀 호출 여러 겹 아래)에서 즉시 빠져나와야
    하므로, on_stmt 훅에서 이 예외를 던지고 factory_shell.run_debug_mode가 받는다.
    """


# ── Stmt/Expr → 소스 줄 번호 ──────────────────────────────────
# AST 노드에 line 필드가 따로 없어서, 노드가 들고 있는 Token들의 line을 재사용해
# "이 Stmt는 대략 몇 번째 줄인가"를 계산한다 (break/step 메시지 출력용).


def get_expr_line(expr: Expr) -> int:
    if isinstance(expr, LiteralExpr):
        return expr.line
    if isinstance(expr, VariableExpr):
        return expr.name.line
    if isinstance(expr, AssignExpr):
        return expr.name.line
    if isinstance(expr, BinaryExpr):
        return get_expr_line(expr.left) or expr.operator.line
    if isinstance(expr, UnaryExpr):
        return expr.operator.line
    if isinstance(expr, GroupingExpr):
        return get_expr_line(expr.expression)
    if isinstance(expr, LogicalExpr):
        return get_expr_line(expr.left) or expr.operator.line
    if isinstance(expr, CallExpr):
        return get_expr_line(expr.callee) or expr.paren.line
    if isinstance(expr, GetExpr):
        return get_expr_line(expr.object) or expr.name.line
    if isinstance(expr, SetExpr):
        return get_expr_line(expr.object) or expr.name.line
    if isinstance(expr, ThisExpr):
        return expr.keyword.line
    if isinstance(expr, SuperExpr):
        return expr.keyword.line
    if isinstance(expr, InstanceOfExpr):
        return get_expr_line(expr.object) or expr.klass.line
    if isinstance(expr, IndexGetExpr):
        return get_expr_line(expr.array) or expr.bracket.line
    if isinstance(expr, IndexSetExpr):
        return get_expr_line(expr.array) or expr.bracket.line
    if isinstance(expr, ArrayExpr):
        return expr.keyword.line
    return 0


def get_stmt_line(stmt: Stmt) -> int:
    if isinstance(stmt, ExpressionStmt):
        return get_expr_line(stmt.expression)
    if isinstance(stmt, PrintStmt):
        return get_expr_line(stmt.expression)
    if isinstance(stmt, VarDeclStmt):
        return stmt.name.line
    if isinstance(stmt, BlockStmt):
        for inner in stmt.statements:
            line = get_stmt_line(inner)
            if line:
                return line
        return 0
    if isinstance(stmt, IfStmt):
        return get_expr_line(stmt.condition) or get_stmt_line(stmt.then_branch)
    if isinstance(stmt, ForStmt):
        if stmt.initializer is not None:
            line = get_stmt_line(stmt.initializer)
            if line:
                return line
        if stmt.condition is not None:
            line = get_expr_line(stmt.condition)
            if line:
                return line
        return get_stmt_line(stmt.body)
    if isinstance(stmt, FuncDeclStmt):
        return stmt.name.line
    if isinstance(stmt, ReturnStmt):
        return stmt.keyword.line
    if isinstance(stmt, ClassDeclStmt):
        return stmt.name.line
    if isinstance(stmt, ImportStmt):
        return stmt.path.line
    return 0


# ── 값 표시 ──────────────────────────────────────────────────


def stringify(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        s = str(value)
        return s[:-2] if s.endswith(".0") else s
    if isinstance(value, list):
        return "[" + ", ".join(stringify(v) for v in value) + "]"
    return str(value)


def type_name(value) -> str:
    if value is None:
        return "Null"
    if isinstance(value, bool):
        return "Boolean"
    if isinstance(value, float):
        return "Number"
    if isinstance(value, str):
        return "String"
    if isinstance(value, list):
        return "Array"
    return type(value).__name__


class DebugController:
    """Executor.on_stmt 훅으로 꽂혀서 Stmt 단위 stepping을 구현한다.

    Executor 자체는 이 클래스를 전혀 모른다 — on_stmt(stmt, depth, executor) 콜백
    하나만 알면 되므로, "실행 로직"과 "디버깅 인터페이스"가 분리되어 있다.
    """

    def __init__(self, source: str):
        self._source_lines = source.splitlines()
        self._breakpoints: set[int] = set()
        self._watches: list[str] = []
        # "step"이 기본값이라 맨 처음 Stmt에서도 별다른 특수 처리 없이 바로 멈춘다.
        self._mode = "step"
        self._next_target_depth = 0

    # ── Executor 훅 ───────────────────────────────────────
    def on_stmt(self, stmt: Stmt, depth: int, executor) -> None:
        line = get_stmt_line(stmt)
        if not self._should_pause(line, depth):
            return
        path = getattr(executor, "path", None) or "<main>"
        print(f"[DEBUG] {path}:{line}번째 줄에서 정지")
        print(f"    → {self._source_line_text(line, executor)}")
        self._print_watches(executor)
        self._command_loop(depth, executor)

    def _should_pause(self, line: int, depth: int) -> bool:
        if line in self._breakpoints:
            return True
        if self._mode == "step":
            return True
        if self._mode == "next":
            return depth <= self._next_target_depth
        return False  # "continue"

    def _source_line_text(self, line: int, executor=None) -> str:
        # executor가 자기 소스를 갖고 있으면(=지금 멈춘 Stmt가 import된 모듈 내부라면)
        # 그 소스를 우선한다 — 그렇지 않으면 항상 최상위 파일 기준으로만 줄을 찾아서,
        # module 내부에서 멈출 때 엉뚱한 파일의 텍스트가 찍힌다.
        source_lines = getattr(executor, "source_lines", None)
        if source_lines is None:
            source_lines = self._source_lines
        if 1 <= line <= len(source_lines):
            return source_lines[line - 1].strip()
        return ""

    # ── 명령어 처리 ───────────────────────────────────────
    def _command_loop(self, depth: int, executor) -> None:
        while True:
            try:
                command = input("> ").strip()
            except EOFError:
                self._mode = "continue"
                return

            if not command:
                continue

            if command in EXIT_COMMANDS:
                print("[DEBUG] 디버그 세션을 종료합니다.")
                raise DebugExit()

            parts = command.split()
            cmd = parts[0]

            if cmd == "step":
                self._mode = "step"
                return
            if cmd == "next":
                self._mode = "next"
                self._next_target_depth = depth
                return
            if cmd == "continue":
                self._mode = "continue"
                return
            if cmd == "break" and len(parts) == 2 and parts[1].isdigit():
                target = int(parts[1])
                self._breakpoints.add(target)
                print(f"[DEBUG] {target}번째 줄에 breakpoint 설정")
                continue
            if cmd == "remove" and len(parts) == 2 and parts[1].isdigit():
                target = int(parts[1])
                self._breakpoints.discard(target)
                print(f"[DEBUG] {target}번째 줄의 breakpoint 해제")
                continue
            if cmd == "breakpoints" and len(parts) == 1:
                self._print_breakpoints()
                continue
            if cmd == "watch" and len(parts) == 2:
                name = parts[1]
                if name not in self._watches:
                    self._watches.append(name)
                print(f"[WATCH] '{name}' 감시 등록")
                continue
            if cmd == "unwatch" and len(parts) == 2:
                name = parts[1]
                if name in self._watches:
                    self._watches.remove(name)
                print(f"[WATCH] '{name}' 감시 해제")
                continue
            if cmd == "watches" and len(parts) == 1:
                self._print_watches(
                    executor, when_empty="[WATCH] 감시 중인 변수가 없습니다."
                )
                continue
            if cmd == "inspect" and len(parts) == 1:
                self._print_scope(executor)
                continue

            print(f"[DEBUG] 알 수 없는 명령어입니다: '{command}'")

    def _print_breakpoints(self) -> None:
        if not self._breakpoints:
            print("[BREAKPOINT] 설정된 breakpoint가 없습니다.")
            return
        for line in sorted(self._breakpoints):
            print(f"[BREAKPOINT] {line}번째 줄")

    def _print_watches(self, executor, when_empty: str | None = None) -> None:
        if not self._watches:
            if when_empty is not None:
                print(when_empty)
            return
        for name in self._watches:
            try:
                value = executor.current_env.get(name)
            except CodeFabRuntimeError:
                continue
            print(f"[WATCH] {name} = {stringify(value)}")

    def _print_scope(self, executor) -> None:
        print("── 현재 스코프 변수 " + "─" * 20)
        env = executor.current_env
        while env is not None:
            tag = "전역" if env.parent is None else "로컬"
            for name, value in env.snapshot().items():
                print(f"[{tag}] {name} = {stringify(value)} ({type_name(value)})")
            env = env.parent
