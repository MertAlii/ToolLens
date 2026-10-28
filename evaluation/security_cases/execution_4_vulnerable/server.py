import yaml
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool()
def parse_value(expression: str) -> object:
    return yaml.load(expression, Loader=yaml.Loader)
if __name__ == "__main__":
    mcp.run(transport="stdio")
