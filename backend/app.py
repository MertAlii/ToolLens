"""Local-only HTTP API for ToolLens. Run from the application root."""
from __future__ import annotations

import asyncio
import json
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import HTMLResponse, Response, StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict, SecretStr

from .core import Workbench, BASE, DATA, ACTIVE
from .analysis import compare
from .storage import now
from . import providers

wb=Workbench()
from .project_chat import ProjectChat
file_chat=ProjectChat(wb.store)
from .github_import import GitHubImports
github_imports=GitHubImports(wb)


@asynccontextmanager
async def lifespan(app):
    yield
    github_imports.close()
    wb.close()
    file_chat.close()
    from . import connection_jobs
    connection_jobs.close()
    try:
        from . import demo_lab
        await demo_lab.close_all()
    except ImportError:pass


app=FastAPI(title='ToolLens',version='0.1.0',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','[::1]','testserver'])
app.add_middleware(CORSMiddleware,allow_origins=['http://localhost:5173','http://127.0.0.1:5173','http://localhost:8000','http://127.0.0.1:8000','http://localhost:8001','http://127.0.0.1:8001','http://localhost:5174','http://127.0.0.1:5174'],allow_credentials=False,allow_methods=['GET','POST','PATCH','DELETE'],allow_headers=['Content-Type','Last-Event-ID'])


class Payload(BaseModel):
    model_config=ConfigDict(extra='forbid')


class ProjectInput(Payload):
    name:str=Field(min_length=1,max_length=120)
    path:str=Field(min_length=1,max_length=3000)


class RemoteInput(Payload):
    probe_id:str|None=None
    name:str=Field(min_length=1,max_length=120)
    url:str=Field(min_length=1,max_length=2000)
    auth_env:str|None=None
    transport:Literal['auto','streamable_http','sse']='auto'


class ConnectionProbeInput(Payload):
    url:str=Field(min_length=1,max_length=2000)
    auth_env:str|None=None
    transport:Literal['auto','streamable_http','sse']='auto'


class GitHubInput(Payload):
    url:str=Field(min_length=1,max_length=500)
    name:str=Field(default='',max_length=120)


class SourceRootInput(Payload):
    path:str=Field(min_length=1,max_length=500)


class ScanInput(Payload):
    profile:Literal['rules_only','ai_review','dynamic']='rules_only'
    provider:str|None=None
    model:str|None=None
    detail:str='normal'


class AnnotationInput(Payload):
    decision:Literal['confirmed','false_positive','needs_review']
    note:str=Field(default='',max_length=4000)


class CompareInput(Payload):
    before_scan_id:str
    after_scan_id:str


class AIInput(Payload):
    message:str=Field(default='',max_length=4000)
    provider:str|None=None
    model:str|None=None
    detail:str='normal'


class ProviderInput(Payload):
    config:dict=Field(default_factory=dict)
    model:str|None=None


class CredentialInput(Payload):
    key:SecretStr
    base_url:str|None=None


class FileQuestion(Payload):
    question:str=Field(min_length=1,max_length=4000)
    paths:list[str]=Field(default_factory=list,max_length=6)
    provider:str|None=None
    model:str|None=None


class ToolCall(Payload):
    name:str
    arguments:dict=Field(default_factory=dict)


def require_scan(scan_id):
    result=wb.scan(scan_id)
    if not result:raise HTTPException(404,'Kontrol bulunamadı.')
    return result


def error(exc):
    return HTTPException(404 if isinstance(exc,KeyError) else 409 if 'zaten çalışıyor' in str(exc) else 400,str(exc))


@app.get('/api/health')
def health():return wb.health()


@app.get('/api/projects')
def projects():return wb.projects()


@app.get('/api/archived-projects')
def archived_projects():return [p for p in wb.store.all('project') if p.get('archived')]


@app.get('/api/folders')
def folders(path:str|None=None):
    from .folders import browse_folders
    try:return browse_folders(path,wb.roots)
    except (ValueError,FileNotFoundError,OSError) as exc:raise error(exc)


@app.post('/api/folders/pick')
def choose_folder():
    from .folders import pick_folder
    try:
        path=pick_folder()
        if path is None:return {'cancelled':True}
        if path not in wb.roots:wb.roots.append(path)
        settings=wb.settings()
        roots=list(dict.fromkeys([*settings.get('selected_project_roots',[]),str(path)]))
        wb.save_settings({'selected_project_roots':roots})
        return {'path':str(path),'name':path.name,'cancelled':False}
    except (ValueError,OSError) as exc:raise error(exc)


@app.get('/api/about')
def about():
    notices=BASE/'THIRD_PARTY_NOTICES.md'
    return Response(notices.read_text(encoding='utf-8') if notices.exists() else 'ToolLens · MCP Sentinel v1.4.0 · MIT',media_type='text/plain; charset=utf-8')


@app.post('/api/projects',status_code=201)
def add_project(value:ProjectInput):
    try:return wb.add_project(value.name,value.path)
    except (ValueError,FileNotFoundError,OSError) as exc:raise error(exc)


@app.post('/api/github-imports',status_code=202)
def import_github(value:GitHubInput):
    try:return github_imports.start(value.url,value.name)
    except (ValueError,OSError) as exc:raise error(exc)


@app.get('/api/github-imports/{job_id}')
def github_import_status(job_id:str):
    try:return github_imports.get(job_id)
    except KeyError as exc:raise error(exc)


@app.post('/api/github-imports/{job_id}/cancel')
def cancel_github_import(job_id:str):
    try:return github_imports.cancel(job_id)
    except KeyError as exc:raise error(exc)


@app.post('/api/connections/probe')
async def probe_mcp_connection(value:ConnectionProbeInput):
    from .connection_probe import probe
    from .probe_receipts import issue
    result=await probe(value.url,value.auth_env,value.transport)
    return issue(value.url,value.auth_env,value.transport,result)


@app.post('/api/projects/remote',status_code=201)
def add_remote_project(value:RemoteInput):
    from .remote_mcp import validate_endpoint
    try:
        url=validate_endpoint(value.url)
        if value.auth_env:
            import re
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,100}',value.auth_env):raise ValueError('Gizli anahtar yerine ortam değişkeninin adını yazın.')
        receipt=None
        if value.probe_id:
            from .probe_receipts import verified
            receipt=verified(value.probe_id,value.url,value.auth_env,value.transport)
        existing=next((p for p in wb.projects() if p.get('endpoint')==url and p.get('auth_env')==value.auth_env and p.get('transport','auto')==value.transport),None)
        if existing:
            if receipt:existing['connection_test']=receipt;wb.store.put('project',existing)
            return existing
        return wb.store.new('project',name=value.name.strip(),kind='remote',language='MCP HTTP',path=url,endpoint=url,auth_env=value.auth_env,transport=value.transport,connection_test=receipt)
    except (ValueError,OSError) as exc:raise error(exc)


@app.post('/api/projects/{project_id}/connection-test')
async def test_mcp_connection(project_id:str):
    project=wb.project(project_id)
    if not project:raise HTTPException(404,'Proje bulunamadı.')
    if project.get('kind')!='remote':raise HTTPException(400,'Bu test HTTP MCP bağlantıları içindir.')
    from .remote_mcp import discover
    from .storage import now
    started=__import__('time').monotonic()
    try:
        tools,server=await discover(project['endpoint'],project.get('auth_env'),transport=project.get('transport','auto'))
        result={'status':'connected','checked_at':now(),'tool_count':len(tools),'server_info':server,'duration_seconds':round(__import__('time').monotonic()-started,2)}
    except (ValueError,InterruptedError) as exc:
        result={'status':'failed','checked_at':now(),'message':str(exc)}
    project['connection_test']=result;wb.store.put('project',project)
    return result


@app.get('/api/projects/{project_id}')
def project(project_id:str):
    value=wb.project(project_id)
    if not value:raise HTTPException(404,'Proje bulunamadı.')
    return value


@app.post('/api/projects/{project_id}/source-root')
def choose_source_root(project_id:str,value:SourceRootInput):
    from .github_import import select_source_root
    try:return select_source_root(wb,project_id,value.path)
    except (ValueError,OSError,KeyError) as exc:raise error(exc)


def local_project(project_id):
    project=wb.project(project_id)
    if not project:raise KeyError('Proje bulunamadı.')
    if project.get('kind')=='remote':raise ValueError('Bu MCP bağlantısında kaynak dosyaları paylaşılmıyor.')
    from .core import validate_path
    return project,validate_path(project['path'],wb.roots)


@app.get('/api/projects/{project_id}/files')
def project_files(project_id:str,path:str=''):
    from .project_files import tree
    try:
        _,root=local_project(project_id)
        return tree(root,path)
    except (ValueError,KeyError,OSError) as exc:raise error(exc)


@app.get('/api/projects/{project_id}/files/index')
def project_file_index(project_id:str):
    from .project_files import index
    try:
        _,root=local_project(project_id)
        return index(root)
    except (ValueError,KeyError,OSError) as exc:raise error(exc)


@app.get('/api/projects/{project_id}/files/content')
def project_file_content(project_id:str,path:str):
    from .project_files import read_file
    try:
        _,root=local_project(project_id)
        return read_file(root,path)
    except (ValueError,KeyError,OSError) as exc:raise error(exc)


@app.get('/api/projects/{project_id}/file-chat')
def file_chat_history(project_id:str):
    try:
        local_project(project_id)
        return file_chat.history(project_id)
    except (ValueError,KeyError,OSError) as exc:raise error(exc)


@app.post('/api/projects/{project_id}/file-chat',status_code=202)
def ask_project_files(project_id:str,value:FileQuestion):
    try:
        project,root=local_project(project_id)
        settings=wb.settings();provider=value.provider or settings.get('default_provider')
        cfg=settings.get('providers',{}).get(provider,{})
        model=value.model or cfg.get('model')
        if not provider or not model or cfg.get('verified_model')!=model:
            raise ValueError('Ayarlar sayfasından bir AI bağlantısı seçip model yanıtını doğrulayın.')
        return file_chat.start(project,root,value.question,value.paths,provider,model,cfg)
    except (ValueError,KeyError,OSError,providers.ProviderError) as exc:raise error(exc)


@app.post('/api/projects/{project_id}/file-chat/{message_id}/cancel')
def cancel_file_question(project_id:str,message_id:str):
    try:
        local_project(project_id)
        return file_chat.cancel(project_id,message_id)
    except (ValueError,KeyError,OSError) as exc:raise error(exc)


@app.get('/api/projects/{project_id}/file-chat/{message_id}/source')
def file_question_source(project_id:str,message_id:str,path:str):
    from .project_files import read_file
    try:
        _,root=local_project(project_id)
        message=file_chat.get(project_id,message_id)
        source=next((f for f in message['source_copies'] if f['path']==path),None)
        if not source:raise KeyError('Bu dosya sorunun bağlamında bulunmuyor.')
        try:unchanged=read_file(root,path)['hash']==source['hash']
        except (ValueError,OSError):unchanged=False
        return {**source,'is_snapshot':True,'current_unchanged':unchanged,'message_id':message_id}
    except (ValueError,KeyError,OSError) as exc:raise error(exc)


@app.delete('/api/projects/{project_id}')
def remove_project(project_id:str):
    try:return wb.archive_project(project_id)
    except (ValueError,KeyError) as exc:raise error(exc)


@app.post('/api/projects/{project_id}/restore')
def restore_project(project_id:str):
    try:return wb.archive_project(project_id,False)
    except (ValueError,KeyError) as exc:raise error(exc)


@app.get('/api/scans')
def scans(project_id:str|None=None):return wb.scans(project_id)


@app.post('/api/projects/{project_id}/scans',status_code=202)
def start_scan(project_id:str,value:ScanInput):
    try:return wb.start_scan(project_id,value.profile,value.provider,value.model,value.detail)
    except (KeyError,ValueError,OSError) as exc:raise error(exc)


@app.get('/api/scans/{scan_id}')
def scan(scan_id:str):
    value=require_scan(scan_id)
    value.pop('source_snapshot',None)
    return value


@app.post('/api/scans/{scan_id}/cancel')
def cancel(scan_id:str):
    try:return wb.cancel(scan_id)
    except KeyError as exc:raise error(exc)


@app.get('/api/scans/{scan_id}/events')
async def events(scan_id:str,request:Request):
    require_scan(scan_id)
    try:after=int(request.headers.get('last-event-id','0'))
    except ValueError:after=0
    async def stream():
        nonlocal after
        while not await request.is_disconnected():
            for event in wb.store.events(scan_id,after):
                after=event['id']
                yield f'id: {after}\nevent: update\ndata: {json.dumps(event,ensure_ascii=False)}\n\n'
            if require_scan(scan_id)['status'] not in ACTIVE:break
            yield ': keepalive\n\n'
            await asyncio.sleep(.6)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})


@app.get('/api/scans/{scan_id}/risk-score')
def scan_risk_score(scan_id:str):
    from .risk_score import calculate_risk
    return calculate_risk(require_scan(scan_id))


@app.get('/api/scans/{scan_id}/findings')
def findings(scan_id:str):return require_scan(scan_id)['findings']


@app.get('/api/scans/{scan_id}/tools')
def tools(scan_id:str):return require_scan(scan_id)['tools']


@app.get('/api/scans/{scan_id}/permissions')
def permissions(scan_id:str):return require_scan(scan_id)['permissions']


@app.get('/api/scans/{scan_id}/sources')
def source(scan_id:str,path:str):
    value=require_scan(scan_id);snapshot=value.get('source_snapshot',{})
    if path not in snapshot.get('files',{}):raise HTTPException(404,'Dosya bu kontrolün kaynak görüntüsünde yok.')
    return {'path':path,'content':snapshot['files'][path],'source_hash':snapshot.get('hash'),'current_unchanged':value.get('source_unchanged')}


@app.get('/api/scans/{scan_id}/logs')
def logs(scan_id:str):
    require_scan(scan_id);job=wb.data/'jobs'/scan_id
    return {'stdout':(job/'stdout.log').read_text(encoding='utf-8',errors='replace')[-16000:] if (job/'stdout.log').exists() else '', 'stderr':(job/'stderr.log').read_text(encoding='utf-8',errors='replace')[-16000:] if (job/'stderr.log').exists() else ''}


@app.post('/api/scans/{scan_id}/findings/{finding_id}/annotations')
def annotate(scan_id:str,finding_id:str,value:AnnotationInput):
    try:return wb.annotate(scan_id,finding_id,value.decision,value.note)
    except (KeyError,ValueError) as exc:raise error(exc)


@app.post('/api/comparisons')
def comparison(value:CompareInput):
    before=require_scan(value.before_scan_id);after=require_scan(value.after_scan_id)
    result=compare(before,after)
    return wb.store.new('comparison',**result)


@app.get('/api/comparisons')
def comparisons():return wb.store.all('comparison')


@app.get('/api/rules')
def rules():
    try:
        from dataclasses import asdict
        from sentinel.static.catalog import RULES
        from sentinel.dynamic.catalog import RULES as DYNAMIC_RULES
        return [asdict(x) for x in RULES]+[x.model_dump(mode='json') for x in DYNAMIC_RULES]
    except ImportError:return []


@app.get('/api/settings')
def settings():return wb.settings()


@app.patch('/api/settings')
def save_settings(value:dict):
    try:return wb.save_settings(value)
    except ValueError as exc:raise error(exc)


@app.get('/api/providers')
def provider_list():return providers.list_providers(wb.settings().get('providers',{}))


@app.post('/api/providers/{provider}/credential')
def save_provider_credential(provider:str,value:CredentialInput):
    from .api_catalog import PRESETS,prepare
    from .credentials import save_key
    if provider not in {'api',*PRESETS}:raise HTTPException(400,'Bu bağlantı API anahtarı kullanmıyor.')
    cfg=prepare(provider,{**wb.settings().get('providers',{}).get(provider,{}),**({'base_url':value.base_url} if value.base_url else {})})
    try:
        from urllib.parse import urlsplit
        origin=str(cfg.get('base_url') or 'https://api.openai.com/v1').rstrip('/')
        parsed=urlsplit(origin)
        if parsed.username or parsed.password or parsed.query or parsed.fragment or (parsed.scheme!='https' and not (parsed.scheme=='http' and parsed.hostname in ('127.0.0.1','localhost','::1'))):raise ValueError('Geçerli bir HTTPS API temel adresi girin.')
        result=save_key(provider,value.key.get_secret_value(),origin)
        settings=wb.settings();profiles=settings.get('providers',{});profiles[provider]={**cfg,'verified_model':None};profiles[provider].pop('_provider_id',None)
        wb.save_settings({'providers':profiles})
        return result
    except ValueError as exc:raise HTTPException(400,str(exc))


@app.get('/api/providers/{provider}/credential')
def provider_credential_status(provider:str):
    from .api_catalog import PRESETS,prepare
    from .credentials import read_key
    if provider not in {'api',*PRESETS}:return {'saved':False}
    cfg=prepare(provider,wb.settings().get('providers',{}).get(provider,{}));origin=str(cfg.get('base_url') or 'https://api.openai.com/v1').rstrip('/')
    return {'saved':bool(read_key(provider,origin)),'storage':'windows_user_encrypted' if os.name=='nt' else 'session_only'}


@app.get('/api/providers/{provider}/models')
def models(provider:str):
    try:return providers.get_models(provider,wb.settings().get('providers',{}).get(provider,{}))
    except providers.ProviderError as exc:raise HTTPException(400,str(exc))


@app.post('/api/providers/{provider}/check')
def check_provider(provider:str,value:ProviderInput):
    try:
        cfg={**wb.settings().get('providers',{}).get(provider,{}),**value.config}
        if value.model:cfg['model']=value.model
        result=providers.check_provider(provider,cfg)
        return result
    except providers.ProviderError as exc:raise HTTPException(400,str(exc))


@app.post('/api/providers/{provider}/test')
def test_provider(provider:str,value:ProviderInput):
    try:
        cfg={**wb.settings().get('providers',{}).get(provider,{}),**value.config}
        model=value.model or cfg.get('model')
        if not model:raise ValueError('Model seçin.')
        return providers.generate(provider,model,'test',{'message':'ToolLens bağlantı kontrolü; yalnız bağlantının çalıştığını söyle.'},config=cfg)
    except (providers.ProviderError,ValueError) as exc:raise HTTPException(400,str(exc))


@app.post('/api/providers/{provider}/test-jobs',status_code=202)
def start_provider_test(provider:str,value:ProviderInput):
    from . import connection_jobs
    cfg={**wb.settings().get('providers',{}).get(provider,{}),**value.config}
    try:return connection_jobs.start(provider,value.model or cfg.get('model'),cfg)
    except ValueError as exc:raise HTTPException(400,str(exc))


@app.get('/api/provider-tests/{job_id}')
def provider_test_status(job_id:str):
    from . import connection_jobs
    try:return connection_jobs.get(job_id)
    except KeyError as exc:raise error(exc)


@app.post('/api/provider-tests/{job_id}/cancel')
def cancel_provider_test(job_id:str):
    from . import connection_jobs
    try:return connection_jobs.cancel(job_id)
    except KeyError as exc:raise error(exc)


def ai_context(scan_id,finding_id,message):
    scan=require_scan(scan_id)
    finding=next((f for f in scan['findings'] if str(f['finding_id'])==finding_id),None)
    if not finding:raise HTTPException(404,'Bulgu bulunamadı.')
    location=finding.get('location',{});path=location.get('path');region=location.get('range',{})
    content=scan.get('source_snapshot',{}).get('files',{}).get(path,'')
    start=max(1,region.get('start_line',1)-12);end=min(len(content.splitlines()),region.get('end_line',start)+24)
    snippet='\n'.join(content.splitlines()[start-1:end])
    try:
        from sentinel.llm.context import sanitize_text
        snippet=sanitize_text(snippet)
    except ImportError:pass
    context={'question':message,'finding':finding,'source':{'path':path,'range':{'start_line':start,'end_line':end},'snippet':snippet},'permissions':[p for p in scan['permissions'] if p['tool_id'] in {t['id'] for t in scan['tools'] if t['path']==path}],'source_hash':scan.get('source_hash')}
    return scan,context


def ask(scan_id,finding_id,value,task):
    scan,context=ai_context(scan_id,finding_id,value.message)
    if task=='patch' and scan.get('analysis_kind')=='remote_contract':raise HTTPException(400,'Kaynak kodu olmayan bağlantıda kod yaması üretilemez. Araç tanımını açıklatabilirsiniz.')
    settings=wb.settings();provider=value.provider or settings.get('default_provider');cfg=settings.get('providers',{}).get(provider,{})
    model=value.model or cfg.get('model')
    if not provider or not model:raise HTTPException(400,'AI Bağlantıları ekranından sağlayıcı ve model seçin.')
    try:answer=providers.generate(provider,model,task,context,detail=value.detail,config=cfg)
    except providers.ProviderError as exc:raise HTTPException(400,str(exc))
    if task=='patch':
        answer.update(applied=False,source_hash=scan.get('source_hash'),scan_id=scan_id,finding_id=finding_id)
        return wb.store.new('patch',**answer)
    return wb.store.new('message',scan_id=scan_id,finding_id=finding_id,question=value.message,**answer)


@app.get('/api/scans/{scan_id}/findings/{finding_id}/messages')
def messages(scan_id:str,finding_id:str):
    require_scan(scan_id)
    return [x for x in wb.store.all('message') if x['scan_id']==scan_id and x['finding_id']==finding_id][::-1]


@app.post('/api/scans/{scan_id}/findings/{finding_id}/messages')
def message(scan_id:str,finding_id:str,value:AIInput):return ask(scan_id,finding_id,value,'explain')


@app.post('/api/scans/{scan_id}/findings/{finding_id}/patch-proposals')
def patch(scan_id:str,finding_id:str,value:AIInput):return ask(scan_id,finding_id,value,'patch')


@app.get('/api/scans/{scan_id}/exports/{format}')
def export(scan_id:str,format:str):
    value=require_scan(scan_id)
    if format=='html':return HTMLResponse(wb.export_html(value),headers={'Content-Disposition':f'inline; filename="toollens-{scan_id}.html"'})
    if format=='json':
        data=value.get('engine_report')
        if not data:raise HTTPException(409,'Motor raporu henüz yok.')
        return Response(json.dumps(data,ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="sentinel-{scan_id}.json"'})
    if format=='toollens':
        value.pop('source_snapshot',None)
        return Response(json.dumps({'schema_version':'toollens-1.0','scan':value},ensure_ascii=False,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename="toollens-{scan_id}.json"'})
    if format=='sarif':
        if not value.get('engine_report'):raise HTTPException(409,'Motor raporu henüz yok.')
        try:
            from sentinel.report.model import ScanReport
            from sentinel.report.json_report import report_model_input
            from sentinel.report.sarif import render_sarif
            data=render_sarif(ScanReport.model_validate_json(report_model_input(value['engine_report'])))
        except Exception:raise HTTPException(500,'Özgün SARIF raporu üretilemedi; JSON motor raporu korunuyor.')
        return Response(data,media_type='application/json',headers={'Content-Disposition':f'attachment; filename="sentinel-{scan_id}.sarif"'})
    raise HTTPException(400,'Desteklenen biçimler: json, toollens, sarif, html.')


def lab():
    from . import demo_lab
    return demo_lab


@app.get('/api/demos')
@app.get('/api/lab')
def demos():return lab().list_demos()


@app.get('/api/demos/{demo_id}/source')
def demo_source(demo_id:str):
    try:return lab().read_source(demo_id)
    except (ValueError,RuntimeError,OSError) as exc:raise HTTPException(404,'Örnek kaynak dosyası bulunamadı.') from exc


@app.post('/api/demos/{demo_id}/register')
def register_demo(demo_id:str):
    candidate=next((d for d in lab().list_demos() if d['id']==demo_id),None)
    if not candidate:raise HTTPException(404,'Örnek bulunamadı.')
    path=Path(candidate['path']).resolve()
    if not any(path.is_relative_to(p) for p in wb.roots):
        # Demo definitions are trusted shipped source; copy only a declared demo directory.
        import shutil
        target=wb.roots[0]/demo_id
        if not target.exists():shutil.copytree(path,target,ignore=shutil.ignore_patterns('__pycache__','.venv','.git'))
        path=target
    try:return wb.add_project(candidate['name'] + (' · Riskli sürüm' if candidate['variant']=='risky' else ' · Düzeltilmiş sürüm'),str(path))
    except (ValueError,OSError) as exc:raise error(exc)


@app.post('/api/demos/{demo_id}/start')
@app.post('/api/lab/{demo_id}/start')
async def demo_start(demo_id:str):
    try:return await lab().start_demo(demo_id)
    except Exception as exc:raise HTTPException(400,str(exc))


@app.post('/api/demos/{demo_id}/stop')
@app.post('/api/lab/{demo_id}/stop')
async def demo_stop(demo_id:str):
    try:return await lab().stop_demo(demo_id)
    except Exception as exc:raise HTTPException(400,str(exc))


@app.get('/api/demos/{demo_id}/tools')
@app.get('/api/lab/{demo_id}/tools')
async def demo_tools(demo_id:str):
    try:return await lab().list_tools(demo_id)
    except Exception as exc:raise HTTPException(400,str(exc))


@app.post('/api/demos/{demo_id}/call')
@app.post('/api/lab/{demo_id}/call')
async def demo_call(demo_id:str,value:ToolCall):
    try:return await lab().call_tool(demo_id,value.name,value.arguments)
    except Exception as exc:raise HTTPException(400,str(exc))


@app.post('/api/lab/prepare-image')
async def prepare_lab_image():
    try:return await asyncio.to_thread(lab().prepare_lab_image)
    except Exception as exc:raise HTTPException(400,str(exc))


dist=BASE/'frontend'/'dist'
if dist.exists():
    if (dist/'assets').exists():app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
    @app.get('/{path:path}')
    def frontend(path:str):
        candidate=(dist/path).resolve()
        if candidate.is_relative_to(dist.resolve()) and candidate.is_file():return FileResponse(candidate)
        if path.startswith('api/'):raise HTTPException(404,'API bulunamadı.')
        return FileResponse(dist/'index.html')
