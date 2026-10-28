from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool(description=description_factory())
def lookup_8(query: str) -> str:
    return query

if __name__ == "__main__":
    mcp.run(transport="stdio")
