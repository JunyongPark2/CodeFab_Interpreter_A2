from interpreter.tokens import KEYWORDS, Token, TokenType

# ── Token.__repr__ ────────────────────────────────────────────────────


def test_token_repr_includes_all_fields():
    token = Token(TokenType.NUMBER, "5", 5.0, line=1, col=3)
    assert repr(token) == "Token(NUMBER, 5, value=5.0, line=1, col=3)"


def test_token_repr_with_default_value_and_position():
    # value/line/col을 명시하지 않으면 각각 None, 0, 0이 기본값이다.
    token = Token(TokenType.EOF, "")
    assert repr(token) == "Token(EOF, , value=None, line=0, col=0)"


# ── KEYWORDS 매핑 ──────────────────────────────────────────────────────


def test_keywords_values_are_all_token_types():
    assert all(isinstance(v, TokenType) for v in KEYWORDS.values())


def test_keywords_lookup_for_known_and_unknown_words():
    assert KEYWORDS.get("if") is TokenType.IF
    assert KEYWORDS.get("not_a_keyword") is None
