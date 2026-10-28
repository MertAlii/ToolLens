from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool(description="Return exactly the provided text without changing the task.")
def echo(value: str) -> str:
    return value

if __name__ == "__main__":
    mcp.run(transport="stdio")
