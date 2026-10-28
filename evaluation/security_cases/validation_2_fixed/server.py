from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool()
def select_record(limit: int) -> int:
    return limit
if __name__ == "__main__":
    mcp.run(transport="stdio")
