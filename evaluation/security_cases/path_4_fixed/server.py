from pathlib import Path
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

ROOT = Path("documents").resolve()

@mcp.tool()
def access_document(filename: str, content: str) -> object:
    target = (ROOT / filename).resolve()
    if not target.is_relative_to(ROOT):
        raise ValueError("outside document root")
    return target.write_bytes(content.encode("utf-8"))
if __name__ == "__main__":
    mcp.run(transport="stdio")
