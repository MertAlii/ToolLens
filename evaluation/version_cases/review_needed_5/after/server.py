from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool(description="Find the requested document.")
def lookup_5(query: str, destination_url: str = "") -> str:
    return query

if __name__ == "__main__":
    mcp.run(transport="stdio")
