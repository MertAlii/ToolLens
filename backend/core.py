"""Durable single-job scan orchestration over an unmodified Sentinel install."""
from __future__ import annotations
from .environment import docker_status,docker_binary,docker_environment

import hashlib
import html
import importlib.metadata
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from .analysis import inventory, permissions, snapshot, compare
from .storage import Store, now
from .decision import summarize_decisions, classify_decision

BASE=Path(__file__).resolve().parents[1]
UPSTREAM=BASE.parents[1]/'work'/'MCP-Sentinel'
DATA=Path(os.environ.get('TOOL_LENS_DATA',str(BASE/'data'))).resolve()
ACTIVE={'queued','running','cancelling'}
STAGES=('preparing','static','inventory','ai','dynamic','reporting')


def validate_path(raw, roots):
    candidate=Path(raw).expanduser()
    if not candidate.is_absolute():candidate=roots[0]/candidate
    path=candidate.resolve(strict=True)
    if not path.is_dir() or path==Path(path.anchor):raise ValueError('Proje yolu var olan bir klasör olmalıdır.')
    if not any(path.is_relative_to(root) for root in roots):raise ValueError('Proje izin verilen çalışma klasörünün dışında.')
    # Reject symlink/junction indirection in the project path as well as sources.
    current=candidate.absolute()
    while current!=current.parent:
        if current.is_symlink() or getattr(current,'is_junction',lambda:False)():raise ValueError('Sembolik bağlantı veya junction proje yolu kabul edilmez.')
        current=current.parent
    return path


def scanner_python():
    default=BASE/'.venv'/('Scripts/python.exe' if os.name=='nt' else 'bin/python')
    return os.environ.get('TOOL_LENS_SENTINEL_PYTHON',str(default if default.exists() else Path(sys.executable)))


def scanner_environment():
    env=docker_environment()
    if (UPSTREAM/'src').exists():env['PYTHONPATH']=str(UPSTREAM/'src')+os.pathsep+env.get('PYTHONPATH','')
    env['PYTHONUTF8']='1';env['PYTHONIOENCODING']='utf-8';env['PYTHONDONTWRITEBYTECODE']='1'
    if os.name=='nt':
        # Windows AF_UNIX socketpair in Semgrep rejects very long TEMP paths.
        # Use a short workspace-owned directory, without changing global settings.
        short=next((p/'tl-tmp' for p in BASE.parents if p.name.lower()=='codex'),None)
        if short is not None:
            short.mkdir(exist_ok=True)
            env['TEMP']=str(short);env['TMP']=str(short)
    # Rules-only selection is explicit, not merely absence of API credentials.
    return env


def docker_available():
    from .environment import docker_status,docker_binary,docker_environment
    return docker_status()['available']


def safe_terminate(proc):
    if proc is None or proc.poll() is not None:return
    if os.name=='nt':
        subprocess.run(['taskkill','/PID',str(proc.pid),'/T','/F'],capture_output=True,timeout=12,creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        import signal
        try:os.killpg(proc.pid,signal.SIGTERM)
        except ProcessLookupError:pass
    try:proc.wait(timeout=10)
    except subprocess.TimeoutExpired:proc.kill()


def _finding_summary(findings):
    counts={x:0 for x in ('Critical','High','Medium','Low','Informational')}
    for item in findings:counts[item.get('severity','Informational')]=counts.get(item.get('severity','Informational'),0)+1
    return {'total':len(findings),'by_severity':counts}


def review_packet(scan_id,findings,files):
    """Bounded saved-source context, never a live read or executable project."""
    sources=[]
    for finding in findings[:10]:
        location=finding.get('location',{});path=location.get('path')
        if path not in files:continue
        lines=files[path].splitlines()
        start=max(1,location.get('range',{}).get('start_line',1)-4)
        selected=[];size=0
        for line in lines[start-1:start+15]:
            if size+len(line)+1>3000:break
            selected.append(line);size+=len(line)+1
        if selected:sources.append({'path':path,'range':{'start_line':start,'end_line':start+len(selected)-1},'snippet':'\n'.join(selected)})
    if not findings:
        # No engine findings is still useful context: supply real entry/source
        # evidence rather than ask the model to explain an empty evidence pack.
        candidates=sorted(files,key=lambda p:(not any(x in files[p] for x in ('@mcp.tool','@server.tool','McpServer','MCPServer','FastMCP','registerTool')),p))
        budget=11000
        for path in candidates:
            if len(sources)>=4 or budget<300:break
            if not path.endswith(('.py','.ts','.mts','.cts')):continue
            lines=files[path].splitlines();selected=[];size=0
            for line in lines:
                if size+len(line)+1>min(budget,4000):break
                selected.append(line);size+=len(line)+1
            if selected:
                sources.append({'path':path,'range':{'start_line':1,'end_line':len(selected)},'snippet':'\n'.join(selected)})
                budget-=size
    return {'scan_id':scan_id,'findings':findings[:10],'sources':sources,'scope':'Desteklenen statik kod incelemesi; çalışma anında test yok. Kaynak örnekleri sınırlandırılmıştır.','finding_count':len(findings),'total_source_files':len(files),'provided_source_files':len({s['path'] for s in sources}),'engine_result':'risk_bulgusu_var' if findings else 'desteklenen_kurallarda_risk_bulgusu_yok','instruction':'Sonucu doğrudan açıkla. Kanıt yetersizse bilinmiyor de; boş pakete benzetme yapma. Kullanım kararı için kapsamı belirt.'}


class Workbench:
    def __init__(self,data=DATA):
        self.data=Path(data).resolve();self.data.mkdir(parents=True,exist_ok=True)
        default=self.data/'projects';default.mkdir(exist_ok=True)
        configured=os.environ.get('TOOL_LENS_PROJECT_ROOTS','')
        self.roots=[default.resolve()]+[Path(p).resolve() for p in configured.split(os.pathsep) if p]
        self.store=Store(self.data/'toollens.sqlite3');self.store.recover()
        for raw in self.settings().get('selected_project_roots',[]):
            try:
                root=Path(raw).resolve(strict=True)
                validate_path(str(root),[root])
                if root not in self.roots:self.roots.append(root)
            except (ValueError,OSError):pass
        self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='toollens')
        self.cancel_events={};self.processes={};self.lock=threading.RLock()

    def health(self):
        try:
            result=subprocess.run([scanner_python(),'-m','sentinel','--version'],capture_output=True,text=True,encoding='utf-8',errors='replace',env=scanner_environment(),timeout=8,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
            sentinel={'available':result.returncode==0,'version':result.stdout.strip() if result.returncode==0 else None,'message':None if result.returncode==0 else 'Sentinel kurulumu tamamlanmalı.'}
        except (OSError,subprocess.TimeoutExpired):sentinel={'available':False,'version':None,'message':'Sentinel başlatılamadı.'}
        return {'status':'ok','sentinel':sentinel,'docker':docker_status(),'allowed_roots':[str(x) for x in self.roots],'data_directory':str(self.data),'single_user':True}

    def projects(self):
        projects=[p for p in self.store.all('project') if not p.get('archived')];scans=self.store.all('scan')
        for project in projects:project['last_scan']=next((self.brief(self.scan(x['id'])) for x in scans if x['project_id']==project['id']),None)
        return projects

    def add_project(self,name,path):
        name=name.strip()
        if not 1<=len(name)<=120:raise ValueError('Proje adı 1–120 karakter olmalıdır.')
        root=validate_path(path,self.roots)
        existing=next((p for p in self.store.all('project') if p['path']==str(root)),None)
        if existing:
            if existing.get('archived'):
                existing['archived']=False
                self.store.put('project',existing)
            return existing
        language='Python' if any(root.glob('**/*.py')) else 'TypeScript' if any(root.glob('**/*.ts')) else 'Unknown'
        return self.store.new('project',name=name,path=str(root),language=language)

    def project(self,key):
        return next((p for p in self.projects() if p['id']==key),None)

    def archive_project(self,key,archived=True):
        with self.lock:
            project=self.store.get('project',key)
            if not project:raise KeyError('Proje bulunamadı.')
            if any(s['project_id']==key and s['status'] in ACTIVE for s in self.store.all('scan')):raise ValueError('Kontrol devam ederken proje kaldırılamaz.')
            if archived and any(m['project_id']==key and m['status'] in ('queued','running') for m in self.store.all('file_chat')):raise ValueError('Bu proje için dosya sorusu yanıtlanıyor. Önce soruyu iptal edin veya yanıtı bekleyin.')
            project['archived']=archived
            self.store.put('project',project)
        return {'id':key,'archived':archived,'source_files_changed':False}

    @staticmethod
    def brief(scan):
        return {k:v for k,v in scan.items() if k not in ('engine_report','runtime_report','source_snapshot','tools','permissions','findings','ai_reviews')}

    def scans(self,project_id=None):
        return [self.brief(self.scan(x['id'])) for x in self.store.all('scan') if project_id is None or x['project_id']==project_id]

    def scan(self,key):
        scan=self.store.get('scan',key)
        if scan:
            notes={x['finding_id']:x for x in self.store.all('annotation') if x['scan_id']==key}
            scan['findings']=[{**f,'annotation':notes.get(str(f['finding_id']))} for f in scan.get('findings',[])]
            scan['findings']=[{**f,'decision':classify_decision(f)} for f in scan['findings']]
            scan['decision_summary']=summarize_decisions(scan['findings'])
            from .risk_score import calculate_risk
            scan['risk_score']=calculate_risk(scan)
        return scan

    def _update(self,key,**fields):
        with self.lock:
            scan=self.store.get('scan',key)
            scan.update(fields);self.store.put('scan',scan)
        return scan

    def _stage(self,key,name,status,reason=None):
        with self.lock:
            scan=self.store.get('scan',key)
            scan['stages']=[{**stage,'status':status,'reason':reason} if stage['name']==name else stage for stage in scan['stages']]
            self.store.put('scan',scan)
            self.store.event(key,'stage',name=name,status=status,reason=reason)

    def start_scan(self,project_id,profile='rules_only',provider=None,model=None,detail='normal'):
        project=self.project(project_id)
        if not project:raise KeyError('Proje bulunamadı.')
        if profile not in ('rules_only','ai_review','dynamic'):raise ValueError('Bilinmeyen kontrol profili.')
        remote=project.get('kind')=='remote'
        if not remote:validate_path(project['path'],self.roots)
        if remote and profile=='dynamic':raise ValueError('URL bağlantılarında araçlar otomatik çalıştırılmaz. Araç tanımı incelemesini seçin.')
        if profile=='dynamic':
            if project['language']!='Python':raise ValueError('İzole davranış testi Python hedefleriyle sınırlıdır.')
            if not docker_available():raise ValueError('Docker çalışmıyor. Temel kontrol Docker olmadan kullanılabilir.')
        if profile=='ai_review' and (not provider or not model):raise ValueError('AI kontrolü için sağlayıcı ve model seçin.')
        with self.lock:
            if any(x['status'] in ACTIVE for x in self.store.all('scan')):raise ValueError('Bir kontrol zaten çalışıyor. Tamamlanmasını bekleyin.')
            scan=self.store.new('scan',project_id=project_id,project_name=project['name'],profile=profile,provider=provider,model=model,status='queued',analysis_complete=False,started_at=None,completed_at=None,error=None,stages=[{'name':s,'status':'pending','reason':None} for s in STAGES],summary=_finding_summary([]),findings=[],tools=[],permissions=[],warnings=[],engine_report=None,runtime_report=None,ai_reviews=[],source_hash=None,sentinel_version=None)
            self.cancel_events[scan['id']]=threading.Event()
            self.store.event(scan['id'],'queued')
            self.pool.submit(self._run_remote if remote else self._run,scan['id'],project,detail)
        return self.brief(scan)

    def _run_remote(self,key,project,detail):
        import asyncio
        from .remote_mcp import validate_endpoint,discover,analyze_catalog
        try:
            self._update(key,status='running',started_at=now(),analysis_kind='remote_contract',sentinel_version='ToolLens-MCP-HTTP-1')
            self._stage(key,'preparing','running')
            endpoint=validate_endpoint(project['endpoint'])
            self._stage(key,'preparing','succeeded')
            self._stage(key,'static','skipped','Kaynak kod paylaşılmadığı için statik analiz yapılmadı.')
            self._stage(key,'inventory','running')
            raw,server=asyncio.run(discover(endpoint,project.get('auth_env'),self.cancel_events[key],transport=project.get('transport','auto')))
            tools,findings,perms=analyze_catalog(raw)
            digest=hashlib.sha256(json.dumps(raw,sort_keys=True).encode()).hexdigest()
            self._update(key,tools=tools,findings=findings,permissions=perms,summary=_finding_summary(findings),source_hash=digest,server_info=server,selected_rule_ids=['TL-R001','TL-R002'],warnings=[{'code':'remote_scope','message':'Yalnız yayımlanan araç tanımları incelendi. Kaynak kod taranmadı; araçlar çağrılmadı; davranış testi yapılmadı.'}])
            self._stage(key,'inventory','succeeded')
            scan=self.store.get('scan',key);complete=True
            if scan['profile']=='ai_review':
                self._stage(key,'ai','running')
                from . import providers
                try:
                    sources=[];selected_tools=[];budget=11000
                    for tool,definition in zip(tools,raw):
                        content=json.dumps(definition,ensure_ascii=False,indent=2)
                        if len(selected_tools)>=20:break
                        if len(content)>budget:continue
                        sources.append({'path':tool['path'],'range':{'start_line':1,'end_line':len(content.splitlines())},'snippet':content});selected_tools.append(tool);budget-=len(content)
                    packet={'scan_id':key,'tools':selected_tools,'findings':findings[:10],'sources':sources,'total_tool_count':len(tools),'provided_tool_count':len(selected_tools),'scope':'Yalnız araç tanımları; kod ve davranış gözlemi yok.'}
                    review=providers.generate(scan['provider'],scan['model'],'review',packet,detail=detail,cancel_event=self.cancel_events[key],config=self.settings().get('providers',{}).get(scan['provider'],{}))
                    review.update(selected_count=len(selected_tools),candidate_count=len(tools),unit='tool')
                    self._update(key,ai_reviews=[review])
                    self._stage(key,'ai','succeeded')
                    complete=len(selected_tools)==len(tools)
                    if not complete:
                        current=self.store.get('scan',key);self._update(key,warnings=[*current.get('warnings',[]),{'code':'remote_ai_bound','message':f'AI bağlamına {len(tools)} araçtan {len(selected_tools)} tanesi sığdı. Kalan tanımlar AI tarafından incelenmedi.'}])
                except providers.ProviderError as exc:
                    complete=False;self._stage(key,'ai','failed',str(exc))
                    self._update(key,ai_reviews=[{'status':'failed','provider':scan['provider'],'model':scan['model'],'error':str(exc),'selected_count':len(tools[:20])}])
            else:self._stage(key,'ai','skipped','AI yorumu seçilmedi.')
            self._stage(key,'dynamic','skipped','Uzak araçlar çağrılmadı.')
            if self.cancel_events[key].is_set():raise InterruptedError('Kontrol iptal edildi.')
            self._stage(key,'reporting','succeeded')
            self._update(key,status='completed' if complete else 'incomplete',analysis_complete=complete,completed_at=now())
            self.store.event(key,'finished',status='completed' if complete else 'incomplete')
        except Exception as exc:
            cancelled=isinstance(exc,InterruptedError) or self.cancel_events[key].is_set()
            state='cancelled' if cancelled else 'failed'
            message=str(exc) if isinstance(exc,(ValueError,InterruptedError)) else 'MCP bağlantısı kurulamadı. HTTP MCP adresini, erişim anahtarını ve sunucunun açık olduğunu kontrol edin.'
            self._finish_stages(key,state);self._update(key,status=state,error=message,analysis_complete=False,completed_at=now())
            self.store.event(key,state,message=message)
        finally:self.cancel_events.pop(key,None)

    def cancel(self,key):
        scan=self.store.get('scan',key)
        if not scan:raise KeyError('Kontrol bulunamadı.')
        if scan['status'] not in ACTIVE:return self.brief(scan)
        self.cancel_events.setdefault(key,threading.Event()).set()
        self._update(key,status='cancelling')
        self.store.event(key,'cancelling')
        return self.brief(self.store.get('scan',key))

    def _run_process(self,key,args,cwd,timeout=1850):
        job=self.data/'jobs'/key;job.mkdir(parents=True,exist_ok=True)
        # Persist diagnostics to bounded files rather than blocking on a full pipe.
        with (job/'stdout.log').open('w',encoding='utf-8') as out,(job/'stderr.log').open('w',encoding='utf-8') as err:
            proc=subprocess.Popen(args,cwd=cwd,env=scanner_environment(),stdout=out,stderr=err,creationflags=(subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP) if os.name=='nt' else 0,start_new_session=os.name!='nt')
            self.processes[key]=proc;deadline=time.monotonic()+timeout
            try:
                while proc.poll() is None:
                    if self.cancel_events[key].is_set():safe_terminate(proc);raise InterruptedError('Kontrol iptal edildi.')
                    if time.monotonic()>deadline:safe_terminate(proc);raise TimeoutError('Kontrol süre sınırına ulaştı; tamamlanmış sayılmadı.')
                    time.sleep(.15)
                if self.cancel_events[key].is_set():raise InterruptedError('Kontrol iptal edildi.')
                return proc.returncode
            finally:self.processes.pop(key,None)

    def _run(self,key,project,detail):
        try:
            if self.cancel_events[key].is_set():raise InterruptedError('Sıradaki kontrol iptal edildi.')
            self._update(key,status='running',started_at=now());self._stage(key,'preparing','running')
            root=validate_path(project['path'],self.roots);source=snapshot(root)
            self._update(key,source_hash=source['hash'],source_snapshot=source)
            self._stage(key,'preparing','succeeded')
            job=self.data/'jobs'/key;job.mkdir(parents=True,exist_ok=True)
            report_path=job/'engine.json'
            self._stage(key,'static','running')
            code=self._run_process(key,[scanner_python(),'-m','backend.static_worker','scan',str(root),'--rules-only','--format','json','--output',str(report_path)],BASE)
            report=None
            if report_path.exists():
                report=json.loads(report_path.read_text(encoding='utf-8'))
            native_report=report
            if not report:
                diagnostic=(job/'stderr.log').read_text(encoding='utf-8',errors='replace')[-6000:] if (job/'stderr.log').exists() else ''
                if 'Timeout' in diagnostic or 'timeout' in diagnostic:
                    reason='Kod incelemesi süre sınırına ulaştı. Tamamlanamayan dosyalar hakkında güvenlik sonucu verilemiyor.'
                elif 'cannot parse TypeScript' in diagnostic or 'PartialParsing' in diagnostic:
                    reason='Kod çözümleyici bazı TypeScript ifadelerini okuyamadı. Bu, tek başına hedef kodun hatalı veya zararlı olduğunu göstermez. İlgili dosyalar teknik günlükte listelenir.'
                elif 'unsupported target' in diagnostic:
                    reason='Bu klasör desteklenen bir MCP projesi olarak tanınmadı. MCP bağımlılığı ve seçilen proje kökünü kontrol edin.'
                else:
                    reason='Kod incelemesi tamamlanamadı. Çıkış kodu ve teknik günlük kaydedildi; kaynak görüntüsü ve erişim bilgileri ayrıca incelenebilir.'
                self._update(key,engine_exit_code=code,engine_diagnostic=diagnostic,error=reason)
                # A ToolLens diagnostic is not an engine report or a clean result.
                report={'findings':[],'analysisComplete':False,'warnings':[{'code':'engine_incomplete','message':reason}]}
            findings=report.get('findings',[])
            complete=bool(report.get('analysisComplete',False) and code in (0,1))
            self._update(key,engine_report=native_report,findings=findings,summary=_finding_summary(findings),sentinel_version=report.get('sentinel_version'),selected_rule_ids=(report.get('static_analysis') or {}).get('selected_rule_ids'),warnings=report.get('warnings',[]),engine_exit_code=code)
            self._stage(key,'static','succeeded' if complete else 'failed','Eksik veya hatalı analiz' if not complete else None)
            self._stage(key,'inventory','running')
            tools,warnings=inventory(source['files']);perms=permissions(tools,source['files'])
            self._update(key,tools=tools,permissions=perms,warnings=[*report.get('warnings',[]),*warnings])
            self._stage(key,'inventory','succeeded')
            scan=self.store.get('scan',key)
            if scan['profile']=='ai_review':
                self._stage(key,'ai','running')
                from . import providers
                settings=self.settings()
                packet=review_packet(key,findings,source['files'])
                if not complete:
                    packet['engine_result']='analiz_tamamlanamadi'
                    packet['instruction']='Statik kontrol eksik. Yalnız sağlanan kaynak örneklerini yorumla; sıfır bulguyu risk yok diye sunma.'
                try:
                    review=providers.generate(scan['provider'],scan['model'],'review',packet,detail=detail,cancel_event=self.cancel_events[key],config=settings.get('providers',{}).get(scan['provider'],{}))
                except providers.ProviderError as exc:
                    review={'provider':scan['provider'],'model':scan['model'],'status':'failed','error':str(exc),'content':'AI incelemesi tamamlanamadı; temel kontrol sonuçları korundu.'}
                review['selected_count']=min(len(findings),10) if findings else len(packet['sources']);review['candidate_count']=len(findings) if findings else len(source['files']);review['unit']='finding' if findings else 'source'
                self._update(key,ai_reviews=[review])
                ok=review.get('status') in ('success','completed','ok')
                self._stage(key,'ai','succeeded' if ok else 'failed',None if ok else review.get('error','AI incelemesi tamamlanamadı.'))
                complete=complete and ok
                if len(findings)>10:
                    complete=False
                    current=self.store.get('scan',key)
                    self._update(key,warnings=[*current['warnings'],{'code':'ai_review_bound','message':'İlk sürüm tek AI turunda en fazla 10 bulgu inceler; kalan bulgular kullanıcı tarafından ayrı incelenebilir.'}])
            else:self._stage(key,'ai','skipped','AI incelemesi seçilmedi.')
            if scan['profile']=='dynamic' and native_report:
                self._stage(key,'dynamic','running')
                runtime_path=job/'runtime.json'
                runtime_code=self._run_process(key,[scanner_python(),'-m','backend.worker',str(root),str(report_path),str(runtime_path)],BASE,timeout=600)
                if runtime_path.exists():
                    runtime=json.loads(runtime_path.read_text(encoding='utf-8'))
                else:
                    diagnostic=(job/'stderr.log').read_text(encoding='utf-8',errors='replace')[-6000:] if (job/'stderr.log').exists() else ''
                    runtime={'complete':False,'execution_successful':False,'findings':[],'warnings':[{'code':'runtime_worker_failed','message':'İzole test tamamlanamadı. Docker imaj hazırlığını ve teknik kontrol günlüğünü inceleyin.'}]}
                    self._update(key,engine_diagnostic=diagnostic,error=runtime['warnings'][0]['message'])
                dynamic_findings=runtime.get('findings',[])
                current=self.store.get('scan',key)
                self._update(key,runtime_report=runtime,runtime_exit_code=runtime_code,findings=[*findings,*dynamic_findings],summary=_finding_summary([*findings,*dynamic_findings]),permissions=permissions(tools,source['files'],runtime),warnings=[*current.get('warnings',[]),*runtime.get('warnings',[])])
                runtime_ok=runtime_code==0 and runtime.get('complete') is True and runtime.get('execution_successful') is True
                complete=complete and runtime_ok
                self._stage(key,'dynamic','succeeded' if runtime_ok else 'failed',None if runtime_ok else 'İzole test tam olarak tamamlanmadı; statik kayıtlar korundu.')
            else:self._stage(key,'dynamic','skipped','İzole davranış testi seçilmedi.')
            if self.cancel_events[key].is_set():raise InterruptedError('Kontrol iptal edildi.')
            self._stage(key,'reporting','running')
            after=snapshot(root)
            unchanged=after['hash']==source['hash']
            if not unchanged:
                complete=False
                current=self.store.get('scan',key)
                self._update(key,warnings=[*current['warnings'],{'code':'source_changed','message':'Kaynak dosyalar kontrol sırasında değişti; kanıtlar güncel sürümle kesin eşleştirilemez.'}])
            self._stage(key,'reporting','succeeded')
            self._update(key,status='completed' if complete else 'incomplete',analysis_complete=complete,completed_at=now(),source_unchanged=unchanged)
            self.store.event(key,'finished',status='completed' if complete else 'incomplete')
        except InterruptedError as exc:
            self._cleanup_containers(key)
            self._finish_stages(key,'cancelled')
            self._update(key,status='cancelled',error=str(exc),analysis_complete=False,completed_at=now());self.store.event(key,'cancelled')
        except Exception as exc:
            self._cleanup_containers(key)
            self._finish_stages(key,'failed')
            self._update(key,status='failed',error=str(exc)[:1200],analysis_complete=False,completed_at=now());self.store.event(key,'failed',message=str(exc)[:1200])
        finally:self.cancel_events.pop(key,None)

    def _finish_stages(self,key,status):
        """A terminated scan must never retain a running stage in the UI."""
        scan=self.store.get('scan',key) or {}
        for stage in scan.get('stages',[]):
            if stage['status']=='running':self._stage(key,stage['name'],status,'Kontrol bu aşamada durdu.')
            elif stage['status']=='pending':self._stage(key,stage['name'],'skipped','Kontrol sonlandığı için çalıştırılmadı.')

    def _cleanup_containers(self,key):
        scan=self.store.get('scan',key) or {};native=scan.get('engine_report') or {}
        scan_id=native.get('scan_id')
        docker=docker_binary()
        if not scan_id or not docker:return
        try:
            result=subprocess.run([docker,'ps','-aq','--filter',f'label=com.securemcp.sentinel.scan_id={scan_id}'],capture_output=True,text=True,timeout=8)
            for container in result.stdout.split():
                if container and all(c in '0123456789abcdef' for c in container.lower()):subprocess.run([docker,'rm','-f',container],capture_output=True,timeout=10)
        except (OSError,subprocess.TimeoutExpired):pass

    def annotate(self,scan_id,finding_id,decision,note):
        scan=self.scan(scan_id)
        if not scan or not any(str(x['finding_id'])==finding_id for x in scan['findings']):raise KeyError('Bulgu bulunamadı.')
        if decision not in ('confirmed','false_positive','needs_review'):raise ValueError('Geçersiz inceleme kararı.')
        if decision=='confirmed' and not note.strip():raise ValueError('Gerçek sorun kararını destekleyen kısa bir inceleme gerekçesi yazın.')
        if len(note)>4000:raise ValueError('Not 4000 karakteri geçemez.')
        return self.store.put('annotation',{'id':f'{scan_id}:{finding_id}','scan_id':scan_id,'finding_id':finding_id,'decision':decision,'note':note,'updated_at':now()})

    def settings(self):
        return (self.store.get('settings','main') or {'id':'main','default_profile':'rules_only','default_provider':None,'providers':{}})

    def save_settings(self,value):
        current=self.settings();current.update(value);current['id']='main'
        # API secrets are supplied through environment variable names, never values.
        for cfg in current.get('providers',{}).values():
            if any(k.lower() in ('api_key','token','password','secret') for k in cfg):raise ValueError('Gizli değer yerine ortam değişkeninin adını kullanın.')
        return self.store.put('settings',current)

    def export_html(self,scan):
        from .reporting import render_report
        return render_report(scan,BASE)

    def close(self):
        for event in list(self.cancel_events.values()):event.set()
        for proc in list(self.processes.values()):safe_terminate(proc)
        self.pool.shutdown(wait=False,cancel_futures=True)
