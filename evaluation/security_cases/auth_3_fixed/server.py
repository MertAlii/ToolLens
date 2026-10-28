import os
from fastapi import FastAPI, Header, HTTPException, Depends
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("toollens-evaluation")

app = FastAPI()

@mcp.tool()
def health() -> str:
    return "ready"

async def verify(authorization: str = Header(...)) -> None:
    expected = os.environ["TOOLLENS_EVAL_TOKEN"]
    if authorization != "Bearer " + expected:
        raise HTTPException(status_code=401)

@app.put("/administration", dependencies=[Depends(verify)])
async def administration() -> dict[str, bool]:
    return {"accepted": True}

if __name__ == "__main__":
    mcp.run(transport="stdio")
