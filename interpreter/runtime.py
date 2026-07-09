from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .errors import CodeFabRuntimeError
from .tokens import Token, TokenType

if TYPE_CHECKING:
    from .ast_nodes import FuncDeclStmt
    from .environment import Environment
    from .executor import Executor


def eval_binary_op(operator, left, right):
    """이진 연산을 수행한다. 타입 불일치나 0으로 나누기 시 CodeFabRuntimeError를 발생시킨다."""
    op = operator.type
    line = operator.line
    numbers = isinstance(left, float) and isinstance(right, float)

    if op == TokenType.PLUS:
        if numbers or (isinstance(left, str) and isinstance(right, str)):
            return left + right
        raise CodeFabRuntimeError(line, "피연산자는 반드시 숫자 또는 문자열이어야 합니다.")
    if op in (TokenType.MINUS, TokenType.STAR, TokenType.GREATER,
              TokenType.LESS, TokenType.GREATER_EQUAL, TokenType.LESS_EQUAL):
        if not numbers:
            raise CodeFabRuntimeError(line, "피연산자는 반드시 숫자여야 합니다.")
    if op == TokenType.MINUS:
        return left - right
    if op == TokenType.STAR:
        return left * right
    if op in (TokenType.SLASH, TokenType.MODULO):
        if not numbers:
            raise CodeFabRuntimeError(line, "피연산자는 반드시 숫자여야 합니다.")
        if right == 0:
            raise CodeFabRuntimeError(line, "0으로 나눈 오류")
        return left / right if op == TokenType.SLASH else left % right
    if op == TokenType.GREATER:
        return left > right
    if op == TokenType.LESS:
        return left < right
    if op == TokenType.GREATER_EQUAL:
        return left >= right
    if op == TokenType.LESS_EQUAL:
        return left <= right
    if op == TokenType.EQUAL_EQUAL:
        return type(left) is type(right) and left == right
    if op == TokenType.BANG_EQUAL:
        return not (type(left) is type(right) and left == right)


def is_truthy(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return True


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


class _ReturnSignal(Exception):
    def __init__(self, value):
        self.value = value


class CodeFabCallable:
    def arity(self) -> int:
        raise NotImplementedError

    def call(self, executor: Executor, arguments: list):
        raise NotImplementedError


class CodeFabFunction(CodeFabCallable):
    def __init__(
        self,
        declaration: FuncDeclStmt,
        closure: Environment,
        is_initializer: bool = False,
    ):
        self._declaration = declaration
        self._closure = closure
        self._is_initializer = is_initializer

    def arity(self) -> int:
        return len(self._declaration.params)

    def bind(self, instance: CodeFabInstance) -> CodeFabFunction:
        from .environment import Environment

        env = Environment(parent=self._closure)
        env.define("This", instance)
        return CodeFabFunction(self._declaration, env, self._is_initializer)

    def call(self, executor: Executor, arguments: list):
        from .environment import Environment

        env = Environment(parent=self._closure)
        for param, arg in zip(self._declaration.params, arguments):
            env.define(param.origin, arg)
        try:
            executor._exec_block(self._declaration.body, env)
        except _ReturnSignal as ret:
            if self._is_initializer:
                return self._closure.get("This", 0)
            return ret.value
        if self._is_initializer:
            return self._closure.get("This", 0)
        return None

    def __str__(self) -> str:
        return f"<function {self._declaration.name.origin}>"


class CodeFabClass(CodeFabCallable):
    def __init__(
        self,
        name: str,
        superclass: Optional[CodeFabClass],
        methods: dict[str, CodeFabFunction],
    ):
        self.name = name
        self.superclass = superclass
        self._methods = methods

    def find_method(self, name: str) -> Optional[CodeFabFunction]:
        if name in self._methods:
            return self._methods[name]
        if self.superclass is not None:
            return self.superclass.find_method(name)
        return None

    def arity(self) -> int:
        initializer = self.find_method("init")
        return initializer.arity() if initializer else 0

    def call(self, executor: Executor, arguments: list) -> CodeFabInstance:
        instance = CodeFabInstance(self)
        initializer = self.find_method("init")
        if initializer is not None:
            initializer.bind(instance).call(executor, arguments)
        return instance

    def __str__(self) -> str:
        return f"<class {self.name}>"


class CodeFabInstance:
    def __init__(self, klass: CodeFabClass):
        self.klass = klass
        self._fields: dict = {}

    def get(self, name: Token):
        if name.origin in self._fields:
            return self._fields[name.origin]
        method = self.klass.find_method(name.origin)
        if method is not None:
            return method.bind(self)
        raise CodeFabRuntimeError(
            name.line, f"'{name.origin}' 속성이 존재하지 않습니다."
        )

    def set(self, name: Token, value) -> None:
        self._fields[name.origin] = value

    def __str__(self) -> str:
        return f"<{self.klass.name} instance>"


class CodeFabModule:
    """import 문으로 만들어지는 런타임 "네임스페이스 객체".

    import된 파일의 최상위 선언(함수/전역변수)들을 fields에 담아 alias 이름으로
    현재 스코프에 정의한다. `.` 로 멤버에 접근하는 문법(GetExpr)은 Class 기능의
    CodeFabInstance를 위해 만들어졌으므로, 그걸 재사용하려면 Executor._eval_get이
    CodeFabModule도 함께 처리하도록 확장해야 한다 (아직 범위 밖) — 그 전까지는
    fields를 직접 조회하는 용도로만 쓰인다.
    """

    def __init__(self, name: str):
        self.name = name
        self.fields: dict = {}

    def get(self, name: str, line: int):
        if name in self.fields:
            return self.fields[name]
        raise CodeFabRuntimeError(
            line, f"모듈 '{self.name}'에 '{name}'이(가) 없습니다."
        )

    def __str__(self) -> str:
        return f"<module {self.name}>"
