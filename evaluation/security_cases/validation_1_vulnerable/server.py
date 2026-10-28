from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

@mcp.tool()
def select_record(arguments: dict[str, object]) -> object:
    return arguments["quantity"]
if __name__ == "__main__":
    mcp.run(transport="stdio")
