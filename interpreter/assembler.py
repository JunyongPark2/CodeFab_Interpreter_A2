# assembler.py — Assembler Unit (Tokenizer + Parser 파이프라인)
#
#   Input  : str                 소스코드 전체 문자열
#   Output : list[Stmt]          AST 루트 Stmt 목록
#   Error  : TokenizeError | ParseError (그대로 전파, 여기서 잡지 않음)

from .ast_nodes import Stmt
from .parser import Parser
from .tokenizer import Tokenizer
from .tokens import Token


class Assembler:
    """소스코드 문자열 → list[Token] → list[Stmt] 파이프라인을 수행한다."""

    def __init__(
        self, tokenizer: type[Tokenizer] = Tokenizer, parser: type[Parser] = Parser
    ):
        # 클래스 자체를 받는다 (assemble()마다 새 소스로 새 인스턴스를 만들기 위해).
        # 테스트 시 가짜(mock) 클래스를 넣으면 Assembler의 연결 로직만 따로 검증할 수 있다.
        self._tokenizer = tokenizer
        self._parser = parser

    def assemble(self, source: str) -> list[Stmt]:
        """소스코드 문자열을 Tokenizer -> Parser 순서로 처리해 AST를 만든다.

        Raises:
            TokenizeError: Tokenizer가 던진 예외를 잡지 않고 그대로 전파한다.
            ParseError: Parser가 던진 예외를 잡지 않고 그대로 전파한다.
        """
        tokens: list[Token] = self._tokenizer(source).tokenize()
        return self._parser(tokens).parse()
