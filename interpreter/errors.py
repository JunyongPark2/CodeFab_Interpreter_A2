class LangRuntimeError(Exception):
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


class ModuleImportError(Exception):
    """import 대상 파일 관련 오류 (파일 없음, 순환 import, 허용되지 않는 구문 포함).

    파이썬 내장 ImportError와 이름이 겹치는 걸 피하기 위해 별도로 정의한다.
    """

    def __init__(self, line: int, msg: str):
        super().__init__(f"[{line}번째줄] {msg}")
