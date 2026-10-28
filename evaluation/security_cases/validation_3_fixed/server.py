from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool()
def select_record(offset: int) -> int:
    return offset
if __name__ == "__main__":
    mcp.run(transport="stdio")
