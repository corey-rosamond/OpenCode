"""Unit tests for condition expression parsing and evaluation."""

import pytest

from code_forge.workflows.conditions import (
    ConditionEvaluator,
    ExpressionLexer,
    ExpressionParser,
    TokenType,
)


class TestExpressionLexer:
    """Tests for ExpressionLexer class."""

    def test_tokenize_simple_identifier(self):
        """Given simple identifier, tokenizes correctly"""
        lexer = ExpressionLexer("step1")
        tokens = lexer.tokenize()

        assert len(tokens) == 2  # identifier + EOF
        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "step1"
        assert tokens[1].type == TokenType.EOF

    def test_tokenize_field_access(self):
        """Given field access expression, tokenizes correctly"""
        lexer = ExpressionLexer("step1.result.value")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.IDENTIFIER
        assert tokens[0].value == "step1"
        assert tokens[1].type == TokenType.DOT
        assert tokens[2].type == TokenType.IDENTIFIER
        assert tokens[2].value == "result"
        assert tokens[3].type == TokenType.DOT
        assert tokens[4].type == TokenType.IDENTIFIER
        assert tokens[4].value == "value"

    def test_tokenize_comparison_operators(self):
        """Given comparison operators, tokenizes correctly"""
        test_cases = [
            ("==", TokenType.EQ),
            ("!=", TokenType.NE),
            ("<", TokenType.LT),
            (">", TokenType.GT),
            ("<=", TokenType.LE),
            (">=", TokenType.GE),
        ]

        for op_str, expected_type in test_cases:
            lexer = ExpressionLexer(f"a {op_str} b")
            tokens = lexer.tokenize()
            assert tokens[1].type == expected_type

    def test_tokenize_boolean_operators(self):
        """Given boolean operators, tokenizes correctly"""
        lexer = ExpressionLexer("a and b or c not d")
        tokens = lexer.tokenize()

        assert tokens[1].type == TokenType.AND
        assert tokens[3].type == TokenType.OR
        assert tokens[5].type == TokenType.NOT

    def test_tokenize_literals(self):
        """Given literals, tokenizes correctly"""
        # Boolean literals
        lexer = ExpressionLexer("true false")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.TRUE
        assert tokens[0].value is True
        assert tokens[1].type == TokenType.FALSE
        assert tokens[1].value is False

        # Number literals
        lexer = ExpressionLexer("42 3.14")
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.NUMBER
        assert tokens[0].value == 42
        assert tokens[1].type == TokenType.NUMBER
        assert tokens[1].value == 3.14

        # String literals
        lexer = ExpressionLexer('"hello" \'world\'')
        tokens = lexer.tokenize()
        assert tokens[0].type == TokenType.STRING
        assert tokens[0].value == "hello"
        assert tokens[1].type == TokenType.STRING
        assert tokens[1].value == "world"

    def test_tokenize_parentheses(self):
        """Given parentheses, tokenizes correctly"""
        lexer = ExpressionLexer("(a and b)")
        tokens = lexer.tokenize()

        assert tokens[0].type == TokenType.LPAREN
        assert tokens[4].type == TokenType.RPAREN

    def test_reject_invalid_character(self):
        """Given invalid character, raises ValueError"""
        lexer = ExpressionLexer("a @ b")
        with pytest.raises(ValueError, match="Unexpected character"):
            lexer.tokenize()

    def test_reject_unterminated_string(self):
        """Given unterminated string, raises ValueError"""
        lexer = ExpressionLexer('"hello')
        with pytest.raises(ValueError, match="Unterminated string"):
            lexer.tokenize()


class TestExpressionParser:
    """Tests for ExpressionParser class."""

    def test_parse_simple_identifier(self):
        """Given simple identifier tokens, parses to AST"""
        lexer = ExpressionLexer("step1")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None

    def test_parse_field_access(self):
        """Given field access tokens, parses to FieldAccessNode"""
        lexer = ExpressionLexer("step1.result")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None

    def test_parse_comparison(self):
        """Given comparison tokens, parses to ComparisonNode"""
        lexer = ExpressionLexer("a == b")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None

    def test_parse_boolean_and(self):
        """Given AND tokens, parses to BooleanOpNode"""
        lexer = ExpressionLexer("a and b")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None

    def test_parse_boolean_or(self):
        """Given OR tokens, parses to BooleanOpNode"""
        lexer = ExpressionLexer("a or b")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None

    def test_parse_boolean_not(self):
        """Given NOT tokens, parses to NotNode"""
        lexer = ExpressionLexer("not a")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None

    def test_parse_complex_expression(self):
        """Given complex expression, parses correctly"""
        lexer = ExpressionLexer("(a and b) or (c > 5)")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None

    def test_parse_nested_field_access(self):
        """Given nested field access, parses correctly"""
        lexer = ExpressionLexer("step.result.data.count")
        tokens = lexer.tokenize()
        parser = ExpressionParser(tokens)

        ast = parser.parse()
        assert ast is not None


class TestConditionEvaluator:
    """Tests for ConditionEvaluator class."""

    def test_evaluate_simple_boolean(self):
        """Given simple boolean literal, evaluates correctly"""
        evaluator = ConditionEvaluator({})

        assert evaluator.evaluate("true") is True
        assert evaluator.evaluate("false") is False

    def test_evaluate_identifier_from_context(self):
        """Given identifier in context as boolean condition, evaluates correctly"""
        context = {"step1": True, "step2": False}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("step1") is True
        assert evaluator.evaluate("step2") is False

    def test_evaluate_field_access(self):
        """Given field access to boolean, evaluates correctly"""
        context = {"step1": {"success": True, "result": {"complete": False}}}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("step1.success") is True
        assert evaluator.evaluate("step1.result.complete") is False

    def test_evaluate_field_value_in_comparison(self):
        """Given field access in comparison, evaluates correctly"""
        context = {"step1": {"result": {"count": 5}}}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("step1.result.count == 5") is True
        assert evaluator.evaluate("step1.result.count > 3") is True
        assert evaluator.evaluate("step1.result.count < 10") is True

    def test_evaluate_missing_field_returns_falsy(self):
        """Given missing field, returns falsy value"""
        context = {"step1": {"success": True}}
        evaluator = ConditionEvaluator(context)

        # Missing field evaluates to falsy (None becomes False)
        result = evaluator.evaluate("step1.nonexistent")
        assert result is False

    def test_evaluate_comparison_equal(self):
        """Given equality comparison, evaluates correctly"""
        context = {"a": 5, "b": 5, "c": 10}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a == b") is True
        assert evaluator.evaluate("a == c") is False

    def test_evaluate_comparison_not_equal(self):
        """Given not equal comparison, evaluates correctly"""
        context = {"a": 5, "b": 10}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a != b") is True
        assert evaluator.evaluate("a != 5") is False

    def test_evaluate_comparison_less_than(self):
        """Given less than comparison, evaluates correctly"""
        context = {"a": 5, "b": 10}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a < b") is True
        assert evaluator.evaluate("b < a") is False

    def test_evaluate_comparison_greater_than(self):
        """Given greater than comparison, evaluates correctly"""
        context = {"a": 10, "b": 5}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a > b") is True
        assert evaluator.evaluate("b > a") is False

    def test_evaluate_comparison_less_equal(self):
        """Given less or equal comparison, evaluates correctly"""
        context = {"a": 5, "b": 5, "c": 10}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a <= b") is True
        assert evaluator.evaluate("a <= c") is True
        assert evaluator.evaluate("c <= a") is False

    def test_evaluate_comparison_greater_equal(self):
        """Given greater or equal comparison, evaluates correctly"""
        context = {"a": 10, "b": 10, "c": 5}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a >= b") is True
        assert evaluator.evaluate("a >= c") is True
        assert evaluator.evaluate("c >= a") is False

    def test_evaluate_string_comparison(self):
        """Given string comparison, evaluates correctly"""
        context = {"status": "done", "other": "pending"}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate('status == "done"') is True
        assert evaluator.evaluate('status == "pending"') is False

    def test_evaluate_boolean_and(self):
        """Given AND expression, evaluates correctly"""
        context = {"a": True, "b": True, "c": False}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a and b") is True
        assert evaluator.evaluate("a and c") is False
        assert evaluator.evaluate("c and a") is False

    def test_evaluate_boolean_or(self):
        """Given OR expression, evaluates correctly"""
        context = {"a": True, "b": False, "c": False}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("a or b") is True
        assert evaluator.evaluate("b or c") is False
        assert evaluator.evaluate("c or a") is True

    def test_evaluate_boolean_not(self):
        """Given NOT expression, evaluates correctly"""
        context = {"a": True, "b": False}
        evaluator = ConditionEvaluator(context)

        assert evaluator.evaluate("not a") is False
        assert evaluator.evaluate("not b") is True

    def test_evaluate_complex_boolean_logic(self):
        """Given complex boolean expression, evaluates correctly"""
        context = {"a": True, "b": False, "c": True, "d": False}
        evaluator = ConditionEvaluator(context)

        # (True and False) or True = True
        assert evaluator.evaluate("(a and b) or c") is True

        # True and (False or True) = True
        assert evaluator.evaluate("a and (b or c)") is True

        # not (True and False) = True
        assert evaluator.evaluate("not (a and b)") is True

    def test_evaluate_mixed_expression(self):
        """Given mixed comparison and boolean expression, evaluates correctly"""
        context = {
            "step1": {"result": {"count": 10}},
            "step2": {"success": True},
        }
        evaluator = ConditionEvaluator(context)

        # count > 5 and success = True
        assert evaluator.evaluate("step1.result.count > 5 and step2.success") is True

        # count < 5 or success = True
        assert evaluator.evaluate("step1.result.count < 5 or step2.success") is True

        # count > 20 and success = False
        assert evaluator.evaluate("step1.result.count > 20 and step2.success") is False

    def test_short_circuit_and(self):
        """Given AND expression, short-circuits on first False"""
        context = {"a": False}
        evaluator = ConditionEvaluator(context)

        # Should not raise error for missing 'b' because 'a' is False
        result = evaluator.evaluate("a and b")
        assert result is False

    def test_short_circuit_or(self):
        """Given OR expression, short-circuits on first True"""
        context = {"a": True}
        evaluator = ConditionEvaluator(context)

        # Should not raise error for missing 'b' because 'a' is True
        result = evaluator.evaluate("a or b")
        assert result is True

    def test_parentheses_precedence(self):
        """Given parentheses, respects precedence"""
        context = {"a": True, "b": False, "c": True}
        evaluator = ConditionEvaluator(context)

        # Without parens: True and False or True = True (AND binds tighter)
        assert evaluator.evaluate("a and b or c") is True

        # With parens: True and (False or True) = True
        assert evaluator.evaluate("a and (b or c)") is True

        # With parens: (True and False) or True = True
        assert evaluator.evaluate("(a and b) or c") is True

    def test_reject_undefined_identifier(self):
        """Given undefined identifier, raises KeyError"""
        evaluator = ConditionEvaluator({})

        with pytest.raises(KeyError, match="Undefined identifier"):
            evaluator.evaluate("nonexistent")

    def test_type_mismatch_returns_false(self):
        """Given type mismatch in comparison, returns False"""
        context = {"a": "string", "b": 42}
        evaluator = ConditionEvaluator(context)

        # Comparing string to number should return False, not crash
        result = evaluator.evaluate("a < b")
        assert result is False
