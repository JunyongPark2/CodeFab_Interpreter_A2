from __future__ import annotations

from typing import Optional, TYPE_CHECKING

from .errors import LangRuntimeError
from .tokens import Token

if TYPE_CHECKING:
    from .ast_nodes import FuncDeclStmt
    from .environment import Environment
    from .executor import Executor


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
        raise LangRuntimeError(name.line, f"'{name.origin}' 속성이 존재하지 않습니다.")

    def set(self, name: Token, value) -> None:
        self._fields[name.origin] = value

    def __str__(self) -> str:
        return f"<{self.klass.name} instance>"
