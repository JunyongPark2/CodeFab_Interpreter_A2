class CodeFabRuntimeError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")


class TokenizeError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")


class ParseError(Exception):
    def __init__(self, line: int, msg: str, incomplete: bool = False):
        self.incomplete = incomplete
        super().__init__(f"[{line}번째줄] {msg}")


class CheckError(Exception):
    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")
