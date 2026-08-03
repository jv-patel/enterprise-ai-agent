"""Calculator tool — safe arithmetic expression evaluation (no `eval`)."""
import ast
import operator

from app.agents.tools.registry import ToolSpec
from app.core.exceptions import ValidationAppError

_ALLOWED_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_ALLOWED_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINARY_OPS:
        return _ALLOWED_BINARY_OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARY_OPS:
        return _ALLOWED_UNARY_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValidationAppError("Expression contains unsupported operations.", error_code="invalid_expression")


async def _calculate(expression: str) -> dict:
    try:
        tree = ast.parse(expression, mode="eval")
        value = _safe_eval(tree.body)
    except ValidationAppError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise ValidationAppError(f"Could not evaluate expression: {exc}", error_code="invalid_expression") from exc
    return {"expression": expression, "result": value}


def build_calculator_tool() -> ToolSpec:
    return ToolSpec(
        name="calculator",
        description=(
            "Evaluate a mathematical expression using standard arithmetic operators "
            "(+, -, *, /, //, %, **) and parentheses. Use for any numeric computation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "The arithmetic expression to evaluate, e.g. '(12 + 8) * 3 / 4'.",
                }
            },
            "required": ["expression"],
        },
        handler=_calculate,
    )
