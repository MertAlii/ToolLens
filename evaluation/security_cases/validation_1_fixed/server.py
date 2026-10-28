from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool()
def select_record(quantity: int) -> int:
    return quantity
if __name__ == "__main__":
    mcp.run(transport="stdio")
