"""Reproducible bounded integration checks. Never starts a risky MCP on the host."""
from __future__ import annotations
import argparse
import concurrent.futures
import json
import shutil
import time
from pathlib import Path
import httpx

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'verification'


def cli_checks():
    from . import providers
    choices={'codex':'gpt-6.1-sol','antigravity':'gemini-3.8-flash-low'}
    def one(provider,model):
        start=time.monotonic()
        try:
            result=providers.generate(provider,model,'test',{'purpose':'ToolLens bağlantı doğrulaması. Yalnız bağlantının çalıştığını bildir. Kaynak dosya veya kişisel veri yok.'},config={'timeout_seconds':45,'validation_retries':0})
            return {'provider':provider,'model':model,'ok':True,'result':result,'seconds':round(time.monotonic()-start,2)}
        except Exception as exc:
            return {'provider':provider,'model':model,'ok':False,'error':str(exc),'seconds':round(time.monotonic()-start,2)}
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda pair:one(*pair),choices.items()))
    OUT.mkdir(exist_ok=True)
    (OUT/'cli-live.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return results


def http_checks(base='http://127.0.0.1:8000'):
    results=[]
    with httpx.Client(base_url=base,timeout=35) as client:
        def req(method,url,**kwargs):
            r=client.request(method,url,**kwargs);r.raise_for_status();return r.json()
        def scan(project):
            record=req('POST',f'/api/projects/{project["id"]}/scans',json={'profile':'rules_only'})
            deadline=time.monotonic()+90
            while time.monotonic()<deadline:
                current=req('GET',f'/api/scans/{record["id"]}')
                if current['status'] not in ('queued','running','cancelling'):
                    return current
                time.sleep(.4)
            raise AssertionError('Actual scan did not finish within bounded verification window')
        health=req('GET','/api/health')
        results.append({'test':'health','ok':health['status']=='ok','sentinel':health['sentinel'],'docker':health['docker']})
        for demo in ('calculator_risky','calculator_fixed','documents_risky','documents_fixed'):
            project=req('POST',f'/api/demos/{demo}/register',json={})
            result=scan(project)
            results.append({'test':'real_static_'+demo,'ok':result['analysis_complete'] is True,'scan_id':result['id'],'status':result['status'],'rules':[f['rule_id'] for f in result['findings']],'count':len(result['findings']),'decision_summary':result['decision_summary']})
            for fmt in ('json','toollens','sarif','html'):
                response=client.get(f'/api/scans/{result["id"]}/exports/{fmt}')
                response.raise_for_status()
                if fmt=='toollens':assert response.json()['scan']['decision_summary']==result['decision_summary']
                if fmt=='html':assert 'Dörtlü Karar Kutusu' in response.text
            results.append({'test':'exports_'+demo,'ok':True,'formats':['json','toollens','sarif','html']})
        # Same project and rule scope, actual source replacement and repeat scan.
        folder=Path(health['allowed_roots'][0])/'verification-calculator-version-change'
        folder.mkdir(exist_ok=True)
        for src in (ROOT/'demos/calculator_risky').iterdir():
            if src.is_file():shutil.copy2(src,folder/src.name)
        project=req('POST','/api/projects',json={'name':'Doğrulama hesaplayıcı sürüm değişikliği','path':str(folder)})
        before=scan(project)
        for src in (ROOT/'demos/calculator_fixed').iterdir():
            if src.is_file():shutil.copy2(src,folder/src.name)
        after=scan(project)
        comparison=req('POST','/api/comparisons',json={'before_scan_id':before['id'],'after_scan_id':after['id']})
        results.append({'test':'same_project_actual_version_change','ok':comparison['comparable'] is True,'before_scan':before['id'],'after_scan':after['id'],'before_rules':[f['rule_id'] for f in before['findings']],'after_rules':[f['rule_id'] for f in after['findings']],'no_longer_observed':len(comparison['findings']['no_longer_observed'])})
        # Runtime calls are to the real SDK server and contain no canned results.
        for demo,tool,arguments in [('calculator_fixed','calculate',{'expression':'2 + 3 * 4'}),('documents_fixed','create_note',{'path':'integration-check.txt','text':'ToolLens gerçek MCP entegrasyon kontrolü'})]:
            req('POST',f'/api/lab/{demo}/start',json={})
            try:
                catalog=req('GET',f'/api/lab/{demo}/tools')
                result=req('POST',f'/api/lab/{demo}/call',json={'name':tool,'arguments':arguments})
                assert not result['is_error']
                if demo=='documents_fixed':
                    read=req('POST',f'/api/lab/{demo}/call',json={'name':'read_note','arguments':{'path':'integration-check.txt'}})
                    assert 'ToolLens gerçek MCP entegrasyon kontrolü' in json.dumps(read,ensure_ascii=False)
                results.append({'test':'live_mcp_'+demo,'ok':True,'tool_count':len(catalog),'actual_response':result})
            finally:
                req('POST',f'/api/lab/{demo}/stop',json={})
        if not health['docker']['available']:
            rejected=client.post('/api/lab/calculator_risky/start',json={})
            assert rejected.status_code==400
            results.append({'test':'risky_host_launch_blocked_without_docker','ok':True,'status_code':rejected.status_code,'detail':rejected.json()['detail']})
    OUT.mkdir(exist_ok=True)
    (OUT/'http-live.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return results


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cli',action='store_true');parser.add_argument('--http',action='store_true');args=parser.parse_args()
    print(json.dumps(cli_checks() if args.cli else http_checks(),ensure_ascii=False,indent=2),flush=True)
