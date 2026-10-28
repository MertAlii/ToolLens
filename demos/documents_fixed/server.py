"""Working MCP notes server with explicit directory containment."""
import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ToolLens Documents Fixed")
DATA = Path(os.environ.get("TOOLLENS_DOCUMENTS", str(Path(__file__).parent / "documents"))).resolve()


def contained(path: str) -> Path:
    if len(path) > 200 or not path or Path(path).is_absolute():
        raise ValueError("Geçerli bir göreli not yolu girin.")
    candidate = (DATA / path).resolve()
    if not candidate.is_relative_to(DATA):
        raise ValueError("Yalnız not klasörünün altındaki dosyalara erişilebilir.")
    if candidate == DATA:
        raise ValueError("Bir dosya adı girilmelidir.")
    if candidate.suffix != ".txt":
        raise ValueError("Not dosyaları .txt uzantılı olmalıdır.")
    return candidate


@mcp.tool()
def create_note(path: str, text: str) -> str:
    """Create a UTF-8 note only inside the configured documents directory."""
    if len(text) > 40_000:
        raise ValueError("Bir not en fazla 40.000 karakter olabilir.")
    destination = contained(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(text, encoding="utf-8")
    return f"Not kaydedildi: {path}"


@mcp.tool()
def read_note(path: str) -> str:
    """Read a note only inside the configured documents directory."""
    destination = contained(path)
    if destination.stat().st_size > 100_000:
        raise ValueError("Not okunabilecek boyutu aşıyor.")
    return destination.read_text(encoding="utf-8")


@mcp.tool()
def list_notes() -> list[str]:
    """List actual .txt notes; symbolic links outside the directory are excluded."""
    return [str(p.relative_to(DATA)) for p in sorted(DATA.rglob("*.txt"))
            if p.is_file() and p.resolve().is_relative_to(DATA)][:200]


@mcp.tool()
def search_notes(query: str) -> list[dict[str, str]]:
    """Search notes in the configured directory."""
    if not query or len(query) > 200:
        raise ValueError("Arama ifadesi 1-200 karakter olmalıdır.")
    matches = []
    for relative in list_notes():
        text = read_note(relative)
        if query.casefold() in text.casefold():
            matches.append({"path": relative, "text": text[:4000]})
        if len(matches) >= 50:
            break
    return matches


if __name__ == "__main__":
    DATA.mkdir(parents=True, exist_ok=True)
    mcp.run(transport="stdio")
