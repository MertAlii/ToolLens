from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool(description="Find the requested document.")
def lookup_2(query: str) -> str:
    return query

if __name__ == "__main__":
    mcp.run(transport="stdio")
