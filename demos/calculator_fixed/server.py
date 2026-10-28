"""A working arithmetic MCP server without executable user code."""
import ast
import math
import operator
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ToolLens Calculator Fixed")
OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
       ast.Div: operator.truediv, ast.Mod: operator.mod, ast.Pow: operator.pow}


def evaluate(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        value = evaluate(node.operand)
        return value if isinstance(node.op, ast.UAdd) else -value
    if isinstance(node, ast.BinOp) and type(node.op) in OPS:
        left, right = evaluate(node.left), evaluate(node.right)
        if isinstance(node.op, ast.Pow) and (abs(right) > 10 or abs(left) > 1_000_000):
            raise ValueError("Üs işlemi sınırı aşıldı.")
        value = OPS[type(node.op)](left, right)
        if not isinstance(value, (int, float)) or not math.isfinite(value) or abs(value) > 1e100:
            raise ValueError("Sonuç sayısal sınırların dışında.")
        return value
    raise ValueError("Yalnız sayılar ve aritmetik işlemler kullanılabilir.")


@mcp.tool()
def calculate(expression: str) -> str:
    """Calculate arithmetic; names, calls, attributes, and executable code are rejected."""
    if not expression or len(expression) > 250:
        raise ValueError("İfade 1-250 karakter olmalıdır.")
    tree = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 64:
        raise ValueError("İfade çok karmaşık.")
    return str(evaluate(tree.body))


if __name__ == "__main__":
    mcp.run(transport="stdio")
