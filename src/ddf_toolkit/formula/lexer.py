"""Formula lexer — tokenizes DDF script formulas.

Based on DeviceLib.pdf Section 2.6 (Formeln).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    # Literals
    NUMBER = auto()
    STRING = auto()
    IDENTIFIER = auto()

    # Operators
    ASSIGN = auto()  # :=
    PLUS = auto()  # +
    MINUS = auto()  # -
    STAR = auto()  # *
    SLASH = auto()  # /
    CARET = auto()  # ^
    EQ = auto()  # ==
    NEQ = auto()  # !=
    LT = auto()  # <
    GT = auto()  # >
    LTE = auto()  # <=
    GTE = auto()  # >=
    AND = auto()  # &&
    ANDNOT = auto()  # &!
    OR = auto()  # ||
    BOR = auto()  # |
    BAND = auto()  # &
    BANDNOT = auto()  # &~
    SHR = auto()  # >>
    SHL = auto()  # <<

    # Delimiters
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    DOT = auto()  # .
    COMMA = auto()  # ,
    SEMICOLON = auto()  # ;
    COLON = auto()  # :

    # Keywords — control flow
    IF = auto()
    THEN = auto()
    ELSE = auto()
    ENDIF = auto()
    SWITCH = auto()
    CASE = auto()
    DEFAULT = auto()
    ENDSWITCH = auto()
    FOR = auto()
    TO = auto()
    BY = auto()
    DO = auto()
    ENDFOR = auto()

    # Special
    DOLLAR = auto()  # $
    EOF = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    position: int


KEYWORDS = {
    "IF": TokenType.IF,
    "THEN": TokenType.THEN,
    "ELSE": TokenType.ELSE,
    "ENDIF": TokenType.ENDIF,
    "SWITCH": TokenType.SWITCH,
    "CASE": TokenType.CASE,
    "DEFAULT": TokenType.DEFAULT,
    "ENDSWITCH": TokenType.ENDSWITCH,
    "FOR": TokenType.FOR,
    "TO": TokenType.TO,
    "BY": TokenType.BY,
    "DO": TokenType.DO,
    "ENDFOR": TokenType.ENDFOR,
}

MAX_FORMULA_SIZE = 4096  # 4 KB cap per PRD §6.3


def tokenize(source: str) -> list[Token]:
    """Tokenize a DDF formula string into tokens."""
    if len(source) > MAX_FORMULA_SIZE:
        msg = f"Formula exceeds {MAX_FORMULA_SIZE} byte limit ({len(source)} bytes)"
        raise ValueError(msg)

    tokens: list[Token] = []
    i = 0
    n = len(source)

    while i < n:
        c = source[i]

        # Whitespace / newlines
        if c in (" ", "\t", "\r", "\n"):
            i += 1
            continue

        # Block comments: /* ... */
        if c == "/" and i + 1 < n and source[i + 1] == "*":
            i += 2
            while i + 1 < n and not (source[i] == "*" and source[i + 1] == "/"):
                i += 1
            i += 2  # skip */
            continue

        # Two-char operators (order matters for disambiguation)
        if i + 1 < n:
            two = source[i : i + 2]
            two_char_map = {
                ":=": TokenType.ASSIGN,
                "==": TokenType.EQ,
                "!=": TokenType.NEQ,
                "<=": TokenType.LTE,
                ">=": TokenType.GTE,
                "&&": TokenType.AND,
                "&!": TokenType.ANDNOT,
                "&~": TokenType.BANDNOT,
                "||": TokenType.OR,
                ">>": TokenType.SHR,
                "<<": TokenType.SHL,
            }
            if two in two_char_map:
                tokens.append(Token(two_char_map[two], two, i))
                i += 2
                continue

        # Single-char operators/delimiters
        single_map = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "^": TokenType.CARET,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ".": TokenType.DOT,
            ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
            ":": TokenType.COLON,
            "$": TokenType.DOLLAR,
            "|": TokenType.BOR,
            "&": TokenType.BAND,
        }
        if c in single_map:
            tokens.append(Token(single_map[c], c, i))
            i += 1
            continue

        # String literals
        if c == "'":
            start = i
            i += 1
            while i < n and source[i] != "'":
                i += 1
            if i < n:
                i += 1  # closing quote
            tokens.append(Token(TokenType.STRING, source[start + 1 : i - 1], start))
            continue

        # Numbers
        if c.isdigit():
            start = i
            while i < n and (source[i].isdigit() or source[i] == "."):
                i += 1
            tokens.append(Token(TokenType.NUMBER, source[start:i], start))
            continue

        # Identifiers and keywords
        if c.isalpha() or c == "_":
            start = i
            while i < n and (source[i].isalnum() or source[i] == "_"):
                i += 1
            word = source[start:i]
            token_type = KEYWORDS.get(word.upper(), TokenType.IDENTIFIER)
            tokens.append(Token(token_type, word, start))
            continue

        # Unknown — skip
        i += 1

    tokens.append(Token(TokenType.EOF, "", n))
    return tokens
