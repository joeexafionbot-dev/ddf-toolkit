"""Recursive-descent parser for the DDF formula scripting language.

Produces a typed AST from a token stream (see lexer.py).
Implements precedence climbing for binary operators.

Grammar (simplified):
    script     = statement*
    statement  = if_stmt | assign_or_expr ";"
    if_stmt    = "IF" expr "THEN" statement* elseif* else? "ENDIF" ";"
    elseif     = "ELSE" "IF" expr "THEN" statement*
    else       = "ELSE" statement*
    assign_or_expr = expr (":=" expr)?
    expr       = or_expr
    or_expr    = and_expr ("||" and_expr)*
    and_expr   = cmp_expr ("&&" cmp_expr)*
    cmp_expr   = add_expr (("==" | "!=" | "<" | ">" | "<=" | ">=") add_expr)*
    add_expr   = mul_expr (("+" | "-") mul_expr)*
    mul_expr   = unary (("*" | "/") unary)*
    unary      = "-" unary | atom
    atom       = NUMBER | STRING | "(" expr ")" | path_or_call
    path_or_call = IDENTIFIER ("." IDENTIFIER | "[" expr "]" | "(" args ")")*
    args       = expr ("," expr)*
"""

from __future__ import annotations

from dataclasses import dataclass

from ddf_toolkit.formula.ast import (
    AssignStmt,
    BinaryOp,
    ElseIfClause,
    Expression,
    ExprStmt,
    FunctionCall,
    Identifier,
    IfStmt,
    IndexAccess,
    NumberLiteral,
    PathAccess,
    ScriptBlock,
    Statement,
    StringLiteral,
    UnaryOp,
)
from ddf_toolkit.formula.lexer import Token, TokenType, tokenize


class FormulaParseError(Exception):
    def __init__(self, message: str, position: int | None = None) -> None:
        self.position = position
        super().__init__(f"Position {position}: {message}" if position is not None else message)


@dataclass
class FormulaAST:
    """Result of parsing a formula."""

    source: str
    tokens: int
    valid: bool
    script: ScriptBlock | None = None
    error: str | None = None

    def __str__(self) -> str:
        if self.valid and self.script:
            n = len(self.script.statements)
            return f"FormulaAST(statements={n}, valid=True)"
        if self.valid:
            return f"FormulaAST(tokens={self.tokens}, valid=True)"
        return f"FormulaAST(valid=False, error={self.error!r})"


class _Parser:
    """Recursive-descent parser with precedence climbing."""

    def __init__(self, tokens: list[Token]) -> None:
        self.tokens = tokens
        self.pos = 0

    def _peek(self) -> Token:
        return self.tokens[self.pos]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _at(self, *types: TokenType) -> bool:
        return self._peek().type in types

    def _expect(self, tt: TokenType) -> Token:
        tok = self._peek()
        if tok.type != tt:
            msg = f"Expected {tt.name}, got {tok.type.name} ({tok.value!r})"
            raise FormulaParseError(msg, tok.position)
        return self._advance()

    def _match(self, *types: TokenType) -> Token | None:
        if self._peek().type in types:
            return self._advance()
        return None

    # -- Top-level -----------------------------------------------------------

    def parse_script(self) -> ScriptBlock:
        stmts: list[Statement] = []
        while not self._at(TokenType.EOF):
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return ScriptBlock(statements=stmts)

    # -- Statements ----------------------------------------------------------

    def _parse_statement(self) -> Statement | None:
        # Skip stray semicolons
        if self._match(TokenType.SEMICOLON):
            return None

        if self._at(TokenType.IF):
            return self._parse_if()

        return self._parse_assign_or_expr()

    def _parse_if(self) -> IfStmt:
        self._expect(TokenType.IF)
        condition = self._parse_expr()
        self._expect(TokenType.THEN)

        then_body = self._parse_block_until(TokenType.ELSE, TokenType.ENDIF)

        elseif_clauses: list[ElseIfClause] = []
        else_body: list[Statement] = []

        while self._match(TokenType.ELSE):
            if self._match(TokenType.IF):
                # ELSE IF clause
                eif_cond = self._parse_expr()
                self._expect(TokenType.THEN)
                eif_body = self._parse_block_until(TokenType.ELSE, TokenType.ENDIF)
                elseif_clauses.append(ElseIfClause(condition=eif_cond, body=eif_body))
            else:
                # Final ELSE
                else_body = self._parse_block_until(TokenType.ENDIF)
                break

        self._expect(TokenType.ENDIF)
        self._match(TokenType.SEMICOLON)

        return IfStmt(
            condition=condition,
            then_body=then_body,
            elseif_clauses=elseif_clauses,
            else_body=else_body,
        )

    def _parse_block_until(self, *terminators: TokenType) -> list[Statement]:
        stmts: list[Statement] = []
        while not self._at(TokenType.EOF) and not self._at(*terminators):
            stmt = self._parse_statement()
            if stmt is not None:
                stmts.append(stmt)
        return stmts

    def _parse_assign_or_expr(self) -> Statement:
        expr = self._parse_expr()

        if self._match(TokenType.ASSIGN):
            value = self._parse_expr()
            self._match(TokenType.SEMICOLON)
            return AssignStmt(target=expr, value=value)

        self._match(TokenType.SEMICOLON)
        return ExprStmt(expr=expr)

    # -- Expressions (precedence climbing) -----------------------------------

    def _parse_expr(self) -> Expression:
        return self._parse_or()

    def _parse_or(self) -> Expression:
        left = self._parse_and()
        while self._at(TokenType.OR):
            op = self._advance().value
            right = self._parse_and()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def _parse_and(self) -> Expression:
        left = self._parse_comparison()
        while self._at(TokenType.AND):
            op = self._advance().value
            right = self._parse_comparison()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def _parse_comparison(self) -> Expression:
        left = self._parse_addition()
        cmp_types = (
            TokenType.EQ,
            TokenType.NEQ,
            TokenType.LT,
            TokenType.GT,
            TokenType.LTE,
            TokenType.GTE,
        )
        while self._at(*cmp_types):
            op = self._advance().value
            right = self._parse_addition()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def _parse_addition(self) -> Expression:
        left = self._parse_multiplication()
        while self._at(TokenType.PLUS, TokenType.MINUS):
            op = self._advance().value
            right = self._parse_multiplication()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def _parse_multiplication(self) -> Expression:
        left = self._parse_unary()
        while self._at(TokenType.STAR, TokenType.SLASH):
            op = self._advance().value
            right = self._parse_unary()
            left = BinaryOp(left=left, op=op, right=right)
        return left

    def _parse_unary(self) -> Expression:
        if self._at(TokenType.MINUS):
            op = self._advance().value
            operand = self._parse_unary()
            return UnaryOp(op=op, operand=operand)
        return self._parse_atom()

    def _parse_atom(self) -> Expression:
        # Number
        if self._at(TokenType.NUMBER):
            tok = self._advance()
            return NumberLiteral(value=float(tok.value))

        # String
        if self._at(TokenType.STRING):
            tok = self._advance()
            return StringLiteral(value=tok.value)

        # Parenthesized expression
        if self._match(TokenType.LPAREN):
            expr = self._parse_expr()
            self._expect(TokenType.RPAREN)
            return expr

        # $ path ($.GPARAM.xxx, $.SYS.TIME, etc.)
        if self._at(TokenType.DOLLAR):
            return self._parse_dollar_path()

        # Identifier: variable, path, or function call
        if self._at(TokenType.IDENTIFIER):
            return self._parse_identifier_chain()

        # Fallback — consume unknown token to avoid infinite loop
        tok = self._advance()
        return Identifier(name=tok.value)

    def _parse_dollar_path(self) -> PathAccess:
        """Parse $-prefixed paths: $.GPARAM.xxx, $.SYS.TIME, $.CONFIG.0"""
        self._advance()  # consume $
        parts = ["$"]
        while self._match(TokenType.DOT):
            if self._at(TokenType.IDENTIFIER) or self._at(TokenType.NUMBER):
                parts.append(self._advance().value)
            else:
                break
        return PathAccess(parts=parts)

    def _parse_identifier_chain(self) -> Expression:
        """Parse identifier followed by dots, brackets, or parens."""
        name = self._advance().value

        # Function call: NAME(args)
        if self._at(TokenType.LPAREN):
            self._advance()
            args: list[Expression] = []
            if not self._at(TokenType.RPAREN):
                args.append(self._parse_expr())
                while self._match(TokenType.COMMA):
                    args.append(self._parse_expr())
            self._expect(TokenType.RPAREN)
            return FunctionCall(name=name, args=args)

        # Path or indexed access: NAME.field.field[idx]
        if self._at(TokenType.DOT):
            parts = [name]
            while self._match(TokenType.DOT):
                if self._at(TokenType.IDENTIFIER) or self._at(TokenType.NUMBER):
                    parts.append(self._advance().value)
                else:
                    break

            result: Expression = PathAccess(parts=parts)

            # Handle trailing [index]
            while self._match(TokenType.LBRACKET):
                idx = self._parse_expr()
                self._expect(TokenType.RBRACKET)
                result = IndexAccess(target=result, index=idx)

                # Continue path after index: value[0].field
                if self._at(TokenType.DOT):
                    more_parts: list[str] = []
                    while self._match(TokenType.DOT):
                        if self._at(TokenType.IDENTIFIER) or self._at(TokenType.NUMBER):
                            more_parts.append(self._advance().value)
                        else:
                            break
                    for part in more_parts:
                        result = BinaryOp(left=result, op=".", right=Identifier(name=part))

            return result

        # Simple identifier
        return Identifier(name=name)


def parse_formula(source: str) -> FormulaAST:
    """Parse a DDF formula string into a typed AST."""
    try:
        tokens = tokenize(source)
        parser = _Parser(tokens)
        script = parser.parse_script()
        script.source = source
        return FormulaAST(
            source=source,
            tokens=len(tokens),
            valid=True,
            script=script,
        )
    except (ValueError, FormulaParseError) as e:
        return FormulaAST(source=source, tokens=0, valid=False, error=str(e))
