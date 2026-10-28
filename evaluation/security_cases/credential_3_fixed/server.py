import os
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")


@mcp.tool()
def credential_is_configured() -> bool:
    return bool(os.environ.get("TOOLLENS_EVAL_API_KEY"))

if __name__ == "__main__":
    mcp.run(transport="stdio")
