import ast
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool()
def parse_value(expression: str) -> object:
    return exec(expression)
if __name__ == "__main__":
    mcp.run(transport="stdio")
