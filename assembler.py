# assembler.py — Assembler Unit (Tokenizer + Parser 파이프라인)
#
#   Input  : str                 소스코드 전체 문자열
#   Output : list[Stmt]          AST 루트 Stmt 목록
#   Error  : TokenizeError | ParseError (그대로 전파, 여기서 잡지 않음)

from ast_nodes import Stmt
from tokens import Token
from tokenizer import Tokenizer
from parser import Parser


class Assembler:
    """소스코드 문자열 → list[Token] → list[Stmt] 파이프라인을 수행한다."""

    def __init__(self, tokenizer: type[Tokenizer] = Tokenizer, parser: type[Parser] = Parser):
        # tokenizer/parser는 인스턴스가 아니라 "클래스" 자체를 받는다 (type[...]).
        # assemble()이 호출될 때마다 새 소스로 새 인스턴스를 만들어야 때문
        # 기본값은 실제 Tokenizer/Parser이고,
        # 테스트할 때는 가짜(mock) 클래스를 넣어서 Assembler의 연결 로직만 따로 검증할 수 있다.
        self._tokenizer = tokenizer
        self._parser = parser

    def assemble(self, source: str) -> list[Stmt]:
        tokens: list[Token] = self._tokenizer(source).tokenize()
        return self._parser(tokens).parse()
