# Inert evaluation credential. Not a real credential.
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

API_KEY = 'ghp_ToolLensEvaluationOnly0123456789'

@mcp.tool()
def credential_is_configured() -> bool:
    return bool(API_KEY)

if __name__ == "__main__":
    mcp.run(transport="stdio")
