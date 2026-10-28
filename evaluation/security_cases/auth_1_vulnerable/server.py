import os
from fastapi import FastAPI, Header, HTTPException, Depends
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

app = FastAPI()

@mcp.tool()
def health() -> str:
    return "ready"

@app.get("/administration")
async def administration() -> dict[str, bool]:
    return {"accepted": True}

if __name__ == "__main__":
    mcp.run(transport="stdio")
