"""Bezpieczny kalkulator: liczy wyrażenia bez uruchamiania dowolnego kodu."""

import ast
import operator

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _eval(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _eval(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        left, right = _eval(node.left), _eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("za duża potęga")
        return _OPS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval(node.operand))
    raise ValueError("nieobsługiwane wyrażenie")


def calculate(expression: str) -> str:
    expr = expression.replace(",", ".").replace("×", "*").replace("÷", "/").replace("^", "**").replace("%", "/100")
    try:
        result = _eval(ast.parse(expr, mode="eval"))
    except ZeroDivisionError:
        return "Błąd: dzielenie przez zero."
    except (SyntaxError, ValueError, TypeError) as e:
        return f"Błąd: nie umiem policzyć '{expression}' ({e})."
    if isinstance(result, float):
        result = round(result, 10)
        if result.is_integer():
            result = int(result)
    return f"{expression} = {result}"
