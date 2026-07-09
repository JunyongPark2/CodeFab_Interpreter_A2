from .ast_nodes import Stmt
from .parser import Parser
from .tokenizer import Tokenizer
from .tokens import Token


class Assembler:
    """소스코드 문자열 → list[Token] → list[Stmt] 파이프라인을 수행한다."""

    def assemble(self, source: str) -> list[Stmt]:
        """소스코드 문자열을 Tokenizer -> Parser 순서로 처리해 AST를 만든다.

        Raises:
            TokenizeError: Tokenizer가 던진 예외를 잡지 않고 그대로 전파한다.
            ParseError: Parser가 던진 예외를 잡지 않고 그대로 전파한다.
        """
        tokens: list[Token] = Tokenizer(source).tokenize()
        return Parser(tokens).parse()
