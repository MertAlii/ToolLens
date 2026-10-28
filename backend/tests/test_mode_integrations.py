import asyncio,json,threading
from pathlib import Path
from unittest.mock import patch
from backend.core import Workbench,scanner_environment
from backend import providers
from backend.storage import Store
from backend import risk_mcp

def test_remote_ai_has_citable_catalog_and_detail_without_executing_tools(tmp_path):
    wb=Workbench(tmp_path/'data')
    key='remote';project={'id':'p','endpoint':'http://127.0.0.1:9999/mcp','kind':'remote','name':'Test HTTP','transport':'sse'}
    wb.store.put('scan',{'id':key,'project_name':'Test HTTP','status':'queued','profile':'ai_review','provider':'codex','model':'unit','findings':[],'stages':[]})
    wb.cancel_events[key]=threading.Event()
    raw=[{'name':'calculate','description':'Calculates numbers.','inputSchema':{'type':'object','properties':{}}}]
    async def discover(*args,**kwargs):
        assert kwargs['transport']=='sse'
        return raw,{'name':'fixture','transport':'sse'}
    def generate(provider,model,task,context,**kwargs):
        assert kwargs['detail']=='simple' and context['provided_tool_count']==1
        source=context['sources'][0]
        assert json.loads(source['snippet'])==raw[0]
        return {**providers._parse_payload({'content':'Tanım incelendi.','evidence_refs':[{'path':source['path'],'start_line':1,'end_line':source['range']['end_line']}],'uncertainties':[],'patch':None},context,'review'),'status':'completed'}
    try:
        with patch('backend.remote_mcp.validate_endpoint',side_effect=lambda x:x),patch('backend.remote_mcp.discover',side_effect=discover),patch.object(providers,'generate',side_effect=generate):wb._run_remote(key,project,'simple')
        scan=wb.scan(key);assert scan['status']=='completed' and scan['analysis_complete']
        assert scan['risk_score']['scope']=='contract_only'
    finally:wb.close()

def test_dynamic_failed_execution_is_incomplete_and_preserves_warnings(tmp_path):
    wb=Workbench(tmp_path/'data')
    root=wb.roots[0]/'sample';root.mkdir();(root/'server.py').write_text('value=1')
    project=wb.add_project('sample',str(root));key='dynamic'
    wb.store.put('scan',{'id':key,'project_name':'sample','status':'queued','profile':'dynamic','findings':[],'stages':[]})
    wb.cancel_events[key]=threading.Event()
    def worker(key,args,cwd,**kwargs):
        job=wb.data/'jobs'/key;job.mkdir(exist_ok=True,parents=True)
        if 'backend.static_worker' in args:(job/'engine.json').write_text(json.dumps({'scan_id':'original','findings':[],'analysisComplete':True}))
        else:(job/'runtime.json').write_text(json.dumps({'complete':True,'execution_successful':False,'findings':[],'warnings':[{'code':'test_warning','message':'runtime warning'}]}))
        return 0
    try:
        with patch.object(wb,'_run_process',side_effect=worker):wb._run(key,project,'simple')
        result=wb.scan(key)
        assert result['status']=='incomplete' and result['risk_score']['value'] is None
        assert any(w['code']=='test_warning' for w in result['warnings'])
    finally:wb.close()

def test_risk_mcp_reads_only_known_store_and_does_not_return_source_or_secret(tmp_path,monkeypatch):
    monkeypatch.setattr(risk_mcp,'DATA',tmp_path)
    key='11111111-1111-4111-8111-111111111111'
    Store(tmp_path/'toollens.sqlite3').put('scan',{'id':key,'status':'completed','analysis_complete':True,'findings':[],'source_snapshot':{'files':{'secret':'PRIVATE_VALUE'}}})
    result=risk_mcp.risk_score(key)
    assert result['risk_score']['value']==0 and 'PRIVATE_VALUE' not in json.dumps(result)
