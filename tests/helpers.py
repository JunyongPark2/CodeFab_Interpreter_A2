from interpreter.tokens import Token, TokenType


def tok(type_, origin="", value=None, line=1, col=1):
    return Token(type=type_, origin=origin, value=value, line=line, col=col)


def name_tok(name, line=1):
    return tok(TokenType.IDENTIFIER, origin=name, line=line)


def path_tok(value: str, line: int = 1) -> Token:
    return Token(TokenType.STRING, f'"{value}"', value, line)
