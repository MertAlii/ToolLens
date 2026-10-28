from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool()
def select_record(record_id: int) -> int:
    return record_id
if __name__ == "__main__":
    mcp.run(transport="stdio")
