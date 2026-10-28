from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool(description="Find a document matching the query.")
def lookup_5(query: str) -> str:
    return query

if __name__ == "__main__":
    mcp.run(transport="stdio")
