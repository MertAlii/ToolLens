"""Read-only ToolLens MCP tools over local Streamable HTTP.

Run: python -m backend.risk_mcp
Endpoint: http://127.0.0.1:8012/mcp
Only ToolLens's own saved scan records are read. Target tools are never called.
"""
from pathlib import Path
import json
import os
import sqlite3
from uuid import UUID
from mcp.server.fastmcp import FastMCP
from .risk_score import calculate_risk

DATA=Path(os.environ.get('TOOL_LENS_DATA',str(Path(__file__).resolve().parents[1]/'data'))).resolve()
mcp=FastMCP('ToolLens Risk',host='127.0.0.1',port=8012,stateless_http=True,json_response=True)

def _read_scans():
    path=DATA/'toollens.sqlite3'
    if not path.is_file():raise ValueError('ToolLens kontrol kaydı henüz yok.')
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=5) as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM records WHERE kind='scan' ORDER BY rowid DESC LIMIT 100")]

@mcp.tool(annotations={'readOnlyHint':True,'destructiveHint':False,'openWorldHint':False})
def list_recent_controls(limit:int=10)->list[dict]:
    """ToolLens'in en son kayıtlı kontrollerinin kimliğini ve kapsamını listeler. Dosya içeriği veya erişim anahtarı döndürmez."""
    if type(limit) is not int or not 1<=limit<=30:raise ValueError('Limit 1 ile 30 arasında olmalı.')
    return [{'scan_id':s['id'],'project':s.get('project_name'),'status':s.get('status'),'profile':s.get('profile')} for s in _read_scans()[:limit]]

@mcp.tool(annotations={'readOnlyHint':True,'destructiveHint':False,'openWorldHint':False})
def risk_score(scan_id:str)->dict:
    """Kayıtlı bir ToolLens kontrolünün gerekçeli 0–100 risk öncelik puanını hesaplar. Eksik analizde sayı üretmez. Puan güvenlik olasılığı değildir; HTTP MCP sonuçları yalnız araç tanımlarını kapsar."""
    try:UUID(scan_id)
    except (ValueError,TypeError,AttributeError):raise ValueError('Geçerli bir kontrol kimliği girin.') from None
    path=DATA/'toollens.sqlite3'
    if not path.is_file():raise ValueError('ToolLens kontrol kaydı henüz yok.')
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True,timeout=5) as db:
        row=db.execute("SELECT payload FROM records WHERE kind='scan' AND id=?",(scan_id,)).fetchone()
    if row is None:raise ValueError('Kontrol bulunamadı.')
    scan=json.loads(row[0])
    return {'scan_id':scan_id,'project':scan.get('project_name'),'risk_score':calculate_risk(scan)}

if __name__=='__main__':mcp.run(transport='streamable-http')
