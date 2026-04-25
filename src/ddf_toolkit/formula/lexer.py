"""Formula lexer — tokenizes DDF script formulas."""

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
    EQ = auto()  # ==
    NEQ = auto()  # !=
    LT = auto()  # <
    GT = auto()  # >
    LTE = auto()  # <=
    GTE = auto()  # >=
    AND = auto()  # &&
    OR = auto()  # ||

    # Delimiters
    LPAREN = auto()  # (
    RPAREN = auto()  # )
    LBRACKET = auto()  # [
    RBRACKET = auto()  # ]
    DOT = auto()  # .
    COMMA = auto()  # ,
    SEMICOLON = auto()  # ;

    # Keywords
    IF = auto()
    THEN = auto()
    ELSE = auto()
    ENDIF = auto()

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

        # Two-char operators
        if i + 1 < n:
            two = source[i : i + 2]
            if two == ":=":
                tokens.append(Token(TokenType.ASSIGN, ":=", i))
                i += 2
                continue
            if two == "==":
                tokens.append(Token(TokenType.EQ, "==", i))
                i += 2
                continue
            if two == "!=":
                tokens.append(Token(TokenType.NEQ, "!=", i))
                i += 2
                continue
            if two == "<=":
                tokens.append(Token(TokenType.LTE, "<=", i))
                i += 2
                continue
            if two == ">=":
                tokens.append(Token(TokenType.GTE, ">=", i))
                i += 2
                continue
            if two == "&&":
                tokens.append(Token(TokenType.AND, "&&", i))
                i += 2
                continue
            if two == "||":
                tokens.append(Token(TokenType.OR, "||", i))
                i += 2
                continue

        # Single-char operators/delimiters
        single_map = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "<": TokenType.LT,
            ">": TokenType.GT,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
            ".": TokenType.DOT,
            ",": TokenType.COMMA,
            ";": TokenType.SEMICOLON,
            "$": TokenType.DOLLAR,
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
