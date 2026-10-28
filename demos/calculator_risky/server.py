"""Intentionally unsafe calculator; actual eval is confined to a Docker lab."""
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ToolLens Calculator Risky")


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a calculation. Laboratory flaw: user text is interpreted as Python."""
    return str(eval(expression))  # Intentionally vulnerable, never host-executed.


if __name__ == "__main__":
    if os.environ.get("TOOLLENS_LAB_ISOLATED") != "1" or not Path("/.dockerenv").exists():
        raise SystemExit("Riskli hesaplayıcı yalnız Docker laboratuvarında çalıştırılabilir.")
    mcp.run(transport="stdio")
