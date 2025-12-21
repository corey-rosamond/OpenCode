"""Conditional execution expression parsing and evaluation.

This module provides a safe expression parser and evaluator for workflow
step conditions. It supports field access, comparisons, and boolean logic
WITHOUT using eval() or exec().

WARNING: This parser is designed to be SAFE. It does NOT use eval(), exec(),
or any other code execution mechanisms. Only whitelisted operations are allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from code_forge.core.logging import get_logger

logger = get_logger(__name__)


class TokenType(Enum):
    """Token types for expression lexer."""

    # Literals
    TRUE = "true"
    FALSE = "false"
    NUMBER = "number"
    STRING = "string"
    IDENTIFIER = "identifier"

    # Operators
    EQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="
    AND = "and"
    OR = "or"
    NOT = "not"

    # Punctuation
    DOT = "."
    LPAREN = "("
    RPAREN = ")"

    # Special
    EOF = "eof"


@dataclass
class Token:
    """A single token from lexing."""

    type: TokenType
    value: Any
    position: int


@dataclass
class ASTNode:
    """Base class for AST nodes."""

    pass


@dataclass
class LiteralNode(ASTNode):
    """Literal value node (true, false, number, string)."""

    value: Any


@dataclass
class IdentifierNode(ASTNode):
    """Identifier node (variable name)."""

    name: str


@dataclass
class FieldAccessNode(ASTNode):
    """Field access node (obj.field)."""

    object: ASTNode
    field: str


@dataclass
class ComparisonNode(ASTNode):
    """Comparison operation node."""

    operator: TokenType
    left: ASTNode
    right: ASTNode


@dataclass
class BooleanOpNode(ASTNode):
    """Boolean operation node (and, or)."""

    operator: TokenType
    left: ASTNode
    right: ASTNode


@dataclass
class NotNode(ASTNode):
    """Not operation node."""

    operand: ASTNode


class ExpressionLexer:
    """Tokenizes condition expressions.

    Converts a condition string into a sequence of tokens.
    """

    def __init__(self, expression: str) -> None:
        """Initialize lexer with expression.

        Args:
            expression: The condition expression to tokenize
        """
        self.expression = expression
        self.position = 0
        self.current_char = self.expression[0] if expression else None

    def advance(self) -> None:
        """Move to next character."""
        self.position += 1
        if self.position < len(self.expression):
            self.current_char = self.expression[self.position]
        else:
            self.current_char = None

    def skip_whitespace(self) -> None:
        """Skip whitespace characters."""
        while self.current_char is not None and self.current_char.isspace():
            self.advance()

    def read_number(self) -> Token:
        """Read a number literal."""
        start_pos = self.position
        num_str = ""

        while self.current_char is not None and (
            self.current_char.isdigit() or self.current_char == "."
        ):
            num_str += self.current_char
            self.advance()

        value = float(num_str) if "." in num_str else int(num_str)
        return Token(TokenType.NUMBER, value, start_pos)

    def read_string(self) -> Token:
        """Read a string literal."""
        start_pos = self.position
        quote_char = self.current_char
        self.advance()  # Skip opening quote

        value = ""
        while self.current_char is not None and self.current_char != quote_char:
            if self.current_char == "\\":
                self.advance()
                if self.current_char in (quote_char, "\\"):
                    value += self.current_char
                    self.advance()
                else:
                    value += "\\"
            else:
                value += self.current_char
                self.advance()

        if self.current_char != quote_char:
            raise ValueError(f"Unterminated string at position {start_pos}")

        self.advance()  # Skip closing quote
        return Token(TokenType.STRING, value, start_pos)

    def read_identifier(self) -> Token:
        """Read an identifier or keyword."""
        start_pos = self.position
        identifier = ""

        while self.current_char is not None and (
            self.current_char.isalnum() or self.current_char in ("_", "-")
        ):
            identifier += self.current_char
            self.advance()

        # Check for keywords
        if identifier == "true":
            return Token(TokenType.TRUE, True, start_pos)
        elif identifier == "false":
            return Token(TokenType.FALSE, False, start_pos)
        elif identifier == "and":
            return Token(TokenType.AND, "and", start_pos)
        elif identifier == "or":
            return Token(TokenType.OR, "or", start_pos)
        elif identifier == "not":
            return Token(TokenType.NOT, "not", start_pos)
        else:
            return Token(TokenType.IDENTIFIER, identifier, start_pos)

    def tokenize(self) -> list[Token]:
        """Tokenize the entire expression.

        Returns:
            List of tokens

        Raises:
            ValueError: If invalid syntax is encountered
        """
        tokens: list[Token] = []

        while self.current_char is not None:
            self.skip_whitespace()

            if self.current_char is None:
                break

            # Numbers
            if self.current_char.isdigit():
                tokens.append(self.read_number())

            # Strings
            elif self.current_char in ('"', "'"):
                tokens.append(self.read_string())

            # Identifiers and keywords
            elif self.current_char.isalpha() or self.current_char == "_":
                tokens.append(self.read_identifier())

            # Operators and punctuation
            elif self.current_char == "=":
                self.advance()
                if self.current_char == "=":
                    tokens.append(Token(TokenType.EQ, "==", self.position - 1))
                    self.advance()
                else:
                    raise ValueError(f"Unexpected '=' at position {self.position - 1}")

            elif self.current_char == "!":
                self.advance()
                if self.current_char == "=":
                    tokens.append(Token(TokenType.NE, "!=", self.position - 1))
                    self.advance()
                else:
                    raise ValueError(f"Unexpected '!' at position {self.position - 1}")

            elif self.current_char == "<":
                start_pos = self.position
                self.advance()
                if self.current_char == "=":
                    tokens.append(Token(TokenType.LE, "<=", start_pos))
                    self.advance()
                else:
                    tokens.append(Token(TokenType.LT, "<", start_pos))

            elif self.current_char == ">":
                start_pos = self.position
                self.advance()
                if self.current_char == "=":
                    tokens.append(Token(TokenType.GE, ">=", start_pos))
                    self.advance()
                else:
                    tokens.append(Token(TokenType.GT, ">", start_pos))

            elif self.current_char == ".":
                tokens.append(Token(TokenType.DOT, ".", self.position))
                self.advance()

            elif self.current_char == "(":
                tokens.append(Token(TokenType.LPAREN, "(", self.position))
                self.advance()

            elif self.current_char == ")":
                tokens.append(Token(TokenType.RPAREN, ")", self.position))
                self.advance()

            else:
                raise ValueError(
                    f"Unexpected character '{self.current_char}' at position {self.position}"
                )

        tokens.append(Token(TokenType.EOF, None, len(self.expression)))
        return tokens


class ExpressionParser:
    """Parses condition expressions into AST.

    Uses recursive descent parsing to build an abstract syntax tree from tokens.
    """

    def __init__(self, tokens: list[Token]) -> None:
        """Initialize parser with tokens.

        Args:
            tokens: List of tokens from lexer
        """
        self.tokens = tokens
        self.position = 0
        self.current_token = tokens[0] if tokens else None

    def advance(self) -> None:
        """Move to next token."""
        self.position += 1
        if self.position < len(self.tokens):
            self.current_token = self.tokens[self.position]

    def parse(self) -> ASTNode:
        """Parse the tokens into an AST.

        Returns:
            Root AST node

        Raises:
            ValueError: If parsing fails
        """
        node = self.parse_or()
        if self.current_token.type != TokenType.EOF:
            raise ValueError(f"Unexpected token: {self.current_token.value}")
        return node

    def parse_or(self) -> ASTNode:
        """Parse OR expressions."""
        left = self.parse_and()

        while self.current_token.type == TokenType.OR:
            self.advance()
            right = self.parse_and()
            left = BooleanOpNode(TokenType.OR, left, right)

        return left

    def parse_and(self) -> ASTNode:
        """Parse AND expressions."""
        left = self.parse_not()

        while self.current_token.type == TokenType.AND:
            self.advance()
            right = self.parse_not()
            left = BooleanOpNode(TokenType.AND, left, right)

        return left

    def parse_not(self) -> ASTNode:
        """Parse NOT expressions."""
        if self.current_token.type == TokenType.NOT:
            self.advance()
            operand = self.parse_not()
            return NotNode(operand)

        return self.parse_comparison()

    def parse_comparison(self) -> ASTNode:
        """Parse comparison expressions."""
        left = self.parse_field_access()

        if self.current_token.type in (
            TokenType.EQ,
            TokenType.NE,
            TokenType.LT,
            TokenType.GT,
            TokenType.LE,
            TokenType.GE,
        ):
            operator = self.current_token.type
            self.advance()
            right = self.parse_field_access()
            return ComparisonNode(operator, left, right)

        return left

    def parse_field_access(self) -> ASTNode:
        """Parse field access expressions (obj.field.subfield)."""
        node = self.parse_primary()

        while self.current_token.type == TokenType.DOT:
            self.advance()
            if self.current_token.type != TokenType.IDENTIFIER:
                raise ValueError(f"Expected identifier after '.', got {self.current_token.type}")

            field = self.current_token.value
            self.advance()
            node = FieldAccessNode(node, field)

        return node

    def parse_primary(self) -> ASTNode:
        """Parse primary expressions (literals, identifiers, parentheses)."""
        token = self.current_token

        # Literals
        if token.type in (TokenType.TRUE, TokenType.FALSE):
            self.advance()
            return LiteralNode(token.value)

        if token.type == TokenType.NUMBER:
            self.advance()
            return LiteralNode(token.value)

        if token.type == TokenType.STRING:
            self.advance()
            return LiteralNode(token.value)

        # Identifiers
        if token.type == TokenType.IDENTIFIER:
            self.advance()
            return IdentifierNode(token.value)

        # Parenthesized expressions
        if token.type == TokenType.LPAREN:
            self.advance()
            node = self.parse_or()
            if self.current_token.type != TokenType.RPAREN:
                raise ValueError("Expected closing parenthesis")
            self.advance()
            return node

        raise ValueError(f"Unexpected token: {token.value}")


class ConditionEvaluator:
    """Evaluates condition expressions safely.

    Evaluates parsed AST nodes against a context of step results.
    """

    def __init__(self, context: dict[str, Any]) -> None:
        """Initialize evaluator with context.

        Args:
            context: Dictionary mapping step IDs to their results
        """
        self.context = context

    def evaluate(self, expression: str) -> bool:
        """Evaluate a condition expression.

        Args:
            expression: Condition string to evaluate

        Returns:
            Boolean result of evaluation

        Raises:
            ValueError: If expression is invalid
        """
        # Tokenize
        lexer = ExpressionLexer(expression)
        tokens = lexer.tokenize()

        # Parse
        parser = ExpressionParser(tokens)
        ast = parser.parse()

        # Evaluate
        result = self._eval_node(ast)

        # Ensure boolean result
        if not isinstance(result, bool):
            logger.warning(f"Condition expression did not return boolean: {expression}")
            return bool(result)

        return result

    def _eval_node(self, node: ASTNode) -> Any:
        """Recursively evaluate an AST node.

        Args:
            node: AST node to evaluate

        Returns:
            Result of evaluating the node
        """
        if isinstance(node, LiteralNode):
            return node.value

        elif isinstance(node, IdentifierNode):
            return self._get_from_context(node.name)

        elif isinstance(node, FieldAccessNode):
            obj = self._eval_node(node.object)
            return self._get_field(obj, node.field)

        elif isinstance(node, ComparisonNode):
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            return self._compare(node.operator, left, right)

        elif isinstance(node, BooleanOpNode):
            left = self._eval_node(node.left)
            if node.operator == TokenType.AND:
                # Short-circuit AND
                if not left:
                    return False
                right = self._eval_node(node.right)
                return bool(left and right)
            elif node.operator == TokenType.OR:
                # Short-circuit OR
                if left:
                    return True
                right = self._eval_node(node.right)
                return bool(left or right)

        elif isinstance(node, NotNode):
            operand = self._eval_node(node.operand)
            return not bool(operand)

        else:
            raise ValueError(f"Unknown AST node type: {type(node)}")

    def _get_from_context(self, name: str) -> Any:
        """Get a value from the context.

        Args:
            name: Variable name

        Returns:
            Value from context

        Raises:
            KeyError: If name not in context
        """
        if name not in self.context:
            logger.warning(f"Identifier '{name}' not found in context")
            raise KeyError(f"Undefined identifier: {name}")

        return self.context[name]

    def _get_field(self, obj: Any, field: str) -> Any:
        """Get a field from an object.

        Args:
            obj: Object to get field from
            field: Field name

        Returns:
            Field value
        """
        # Handle dict access
        if isinstance(obj, dict):
            if field not in obj:
                logger.warning(f"Field '{field}' not found in object")
                return None
            return obj[field]

        # Handle attribute access
        if hasattr(obj, field):
            return getattr(obj, field)

        logger.warning(f"Field '{field}' not found in object of type {type(obj)}")
        return None

    def _compare(self, operator: TokenType, left: Any, right: Any) -> bool:
        """Compare two values.

        Args:
            operator: Comparison operator
            left: Left operand
            right: Right operand

        Returns:
            Boolean comparison result
        """
        try:
            if operator == TokenType.EQ:
                return left == right
            elif operator == TokenType.NE:
                return left != right
            elif operator == TokenType.LT:
                return left < right
            elif operator == TokenType.GT:
                return left > right
            elif operator == TokenType.LE:
                return left <= right
            elif operator == TokenType.GE:
                return left >= right
            else:
                raise ValueError(f"Unknown comparison operator: {operator}")
        except TypeError as e:
            logger.warning(f"Type error in comparison: {e}")
            return False
