"""Import a public GitHub source snapshot without running repository commands."""
from __future__ import annotations

import io
import re
import shutil
import stat
import threading
import time
import zipfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path, PurePosixPath
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from .storage import now

MAX_DOWNLOAD=25*1024*1024
MAX_EXPANDED=100*1024*1024
MAX_FILES=6000


def parse_repository(raw):
    url=urlsplit(raw.strip())
    parts=url.path.rstrip('/').split('/')
    if url.scheme!='https' or url.netloc.lower()!='github.com' or url.query or url.fragment or len(parts)!=3:
        raise ValueError('Herkese açık deponun https://github.com/sahip/depo adresini yazın.')
    owner,repo=parts[1:]
    if repo.endswith('.git'):repo=repo[:-4]
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9-]{0,38}',owner) or not re.fullmatch(r'[A-Za-z0-9_.-]{1,100}',repo) or repo in ('.','..'):
        raise ValueError('GitHub depo adresi geçerli değil.')
    return owner,repo


def extract_source(data:bytes,destination:Path,cancel:threading.Event):
    """Validate the entire archive before writing inside a fresh owned directory."""
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos=archive.infolist()
        if len(infos)>MAX_FILES:raise ValueError('Depo 6000 dosya sınırını aşıyor.')
        if sum(i.file_size for i in infos)>MAX_EXPANDED:raise ValueError('Depo açıldığında 100 MB sınırını aşıyor.')
        roots=set();entries=[];seen=set()
        for info in infos:
            raw=info.orig_filename
            path=PurePosixPath(raw)
            mode=info.external_attr>>16
            if path.is_absolute() or '\x00' in raw or '\\' in raw or ':' in raw or any(p in ('.','..') for p in raw.split('/') if p):
                raise ValueError('Depoda güvenli olmayan dosya yolu var.')
            if stat.S_ISLNK(mode) or info.flag_bits&1:raise ValueError('Bağlantılı veya şifreli arşiv kabul edilmez.')
            if not path.parts:continue
            roots.add(path.parts[0])
            if len(path.parts)==1:continue
            relative=Path(*path.parts[1:])
            if any(p.lower() in ('.git','node_modules','.venv','venv') for p in relative.parts):continue
            key=str(relative).casefold()
            if key in seen:raise ValueError('Depoda çakışan dosya yolları var.')
            seen.add(key)
            # Windows reserved paths cannot silently alias an existing target.
            if any(p.endswith((' ','.')) or re.fullmatch(r'(?i)(con|prn|aux|nul|com[0-9]|lpt[0-9])(\..*)?',p) for p in relative.parts):
                raise ValueError('Depoda bu işletim sistemine uygun olmayan dosya adı var.')
            entries.append((info,relative))
        if len(roots)!=1:raise ValueError('GitHub kaynak arşivi beklenen yapıda değil.')
        for info,relative in entries:
            if cancel.is_set():raise InterruptedError('İndirme iptal edildi.')
            target=destination/relative
            if not target.resolve().is_relative_to(destination.resolve()):raise ValueError('Arşiv yolu proje dışında.')
            if info.is_dir():target.mkdir(parents=True,exist_ok=True)
            else:
                target.parent.mkdir(parents=True,exist_ok=True)
                with archive.open(info) as source,target.open('xb') as out:shutil.copyfileobj(source,out,64*1024)
        return sum(not info.is_dir() for info,_ in entries)


def source_roots(root):
    """Locate manifests and tool declarations by reading source text only."""
    candidates=[]
    for manifest in sorted(root.rglob('*')):
        if manifest.name not in ('pyproject.toml','requirements.txt','package.json') or not manifest.is_file():continue
        relative=manifest.parent.relative_to(root)
        if len(relative.parts)>5 or any(p.startswith('.') for p in relative.parts) or manifest.stat().st_size>256_000:continue
        text=manifest.read_text(encoding='utf-8',errors='replace')
        if not re.search(r'(?im)(fastmcp|(?:^|[\s\"\'])mcp(?:[\s\"\'\[>=~]|$)|@modelcontextprotocol/sdk)',text):continue
        path=relative.as_posix()
        if any(c['path']==path for c in candidates):continue
        candidates.append({'path':path,'language':'TypeScript' if manifest.name=='package.json' else 'Python'})
    return candidates[:40]


def select_source_root(wb,project_id,relative):
    from .core import ACTIVE,validate_path
    from .project_files import safe_path
    with wb.lock:
        project=wb.project(project_id)
        if not project or not project.get('repository_root'):raise ValueError('GitHub kaynak projesi bulunamadı.')
        if any(s['project_id']==project_id and s['status'] in ACTIVE for s in wb.store.all('scan')) or any(m['project_id']==project_id and m['status'] in ('queued','running') for m in wb.store.all('file_chat')):
            raise ValueError('İnceleme devam ederken kaynak klasörü değiştirilemez.')
        root=validate_path(project['repository_root'],wb.roots)
        choices=source_roots(root)
        if relative not in {c['path'] for c in choices}|{'.'}:raise ValueError('Algılanan proje klasörlerinden birini seçin.')
        selected=root if relative=='.' else safe_path(root,relative,directory=True)
        project.update(path=str(selected),repository_subdirectory=relative)
        if relative!='.':project['language']=next(c['language'] for c in choices if c['path']==relative)
        return wb.store.put('project',project)


class GitHubImports:
    def __init__(self,wb):
        self.wb=wb;self.lock=threading.RLock();self.events={};self.pool=ThreadPoolExecutor(max_workers=1,thread_name_prefix='github-source')
        for job in wb.store.all('github_import'):
            if job['status'] in ('queued','running'):
                job.update(status='failed',error='Uygulama indirme tamamlanmadan kapandı.',completed_at=now());wb.store.put('github_import',job)

    def get(self,key):
        job=self.wb.store.get('github_import',key)
        if not job:raise KeyError('GitHub indirmesi bulunamadı.')
        return job

    def start(self,url,name=''):
        owner,repo=parse_repository(url)
        with self.lock:
            if any(j['status'] in ('queued','running') for j in self.wb.store.all('github_import')):raise ValueError('Bir GitHub indirmesi zaten çalışıyor.')
            job=self.wb.store.new('github_import',url=f'https://github.com/{owner}/{repo}',name=name.strip()[:120] or repo,status='queued',stage='Depo bilgisi bekleniyor',downloaded_bytes=0)
            event=threading.Event();self.events[job['id']]=event
            self.pool.submit(self._run,job,owner,repo,event)
            return job

    def cancel(self,key):
        with self.lock:
            job=self.get(key)
            if job['status'] in ('queued','running'):
                self.events[key].set();job['cancellation_requested']=True;self.wb.store.put('github_import',job)
            return job

    def _run(self,job,owner,repo,event):
        start=time.monotonic();root=self.wb.roots[0].resolve();destination=root/f'github-{uuid4().hex}'
        def update(**fields):
            with self.lock:
                job.update(fields);self.wb.store.put('github_import',job)
        try:
            update(status='running',stage='GitHub depo bilgisi alınıyor')
            headers={'Accept':'application/vnd.github+json','User-Agent':'ToolLens-local-source-review'}
            with httpx.Client(timeout=httpx.Timeout(20,read=10),follow_redirects=False,headers=headers,trust_env=False) as client:
                response=client.get(f'https://api.github.com/repos/{owner}/{repo}')
                if response.status_code==404:raise ValueError('Depo bulunamadı. Bu sürüm herkese açık GitHub depolarını destekler.')
                response.raise_for_status();meta=response.json()
                branch=meta.get('default_branch','')
                if not branch:raise ValueError('Deponun varsayılan dalı bulunamadı.')
                from urllib.parse import quote
                revision=client.get(f'https://api.github.com/repos/{owner}/{repo}/commits/{quote(branch,safe="")}');revision.raise_for_status()
                sha=revision.json().get('sha','')
                if not re.fullmatch('[a-f0-9]{40}',sha):raise ValueError('Kaynak sürümü doğrulanamadı.')
                update(stage='Kaynak dosyalar indiriliyor',branch=branch,commit=sha)
                content=bytearray();last=0
                with client.stream('GET',f'https://codeload.github.com/{owner}/{repo}/zip/{sha}') as stream:
                    stream.raise_for_status()
                    for chunk in stream.iter_bytes(64*1024):
                        if event.is_set():raise InterruptedError()
                        if time.monotonic()-start>120:raise ValueError('İndirme iki dakikalık süre sınırını aştı.')
                        content.extend(chunk)
                        if len(content)>MAX_DOWNLOAD:raise ValueError('Sıkıştırılmış kaynak 25 MB sınırını aşıyor.')
                        if len(content)-last>=256*1024: update(downloaded_bytes=len(content));last=len(content)
            if event.is_set():raise InterruptedError()
            update(stage='Dosyalar kontrol edilip hazırlanıyor',downloaded_bytes=len(content))
            destination.mkdir()
            count=extract_source(bytes(content),destination,event)
            with self.lock:
                if event.is_set():raise InterruptedError()
                project=self.wb.add_project(job['name'],str(destination))
                choices=source_roots(destination)
                project.update(repository_url=job['url'],repository_commit=sha,repository_branch=branch,repository_root=str(destination),imported_at=now())
                self.wb.store.put('project',project)
                update(status='completed',stage='Kaynak kod hazır',project_id=project['id'],file_count=count,source_roots=choices,completed_at=now())
        except Exception as exc:
            # Only the generated directory within our managed project root is removed.
            if destination.exists() and destination.parent.resolve()==root and destination.name.startswith('github-'):
                shutil.rmtree(destination)
            cancelled=event.is_set() or isinstance(exc,InterruptedError)
            message='İndirme iptal edildi.' if cancelled else str(exc)[:500]
            if isinstance(exc,httpx.HTTPStatusError):message=f'GitHub yanıtı: {exc.response.status_code}. Depo adresini veya GitHub erişim sınırını kontrol edin.'
            update(status='cancelled' if cancelled else 'failed',error=message,completed_at=now())
        finally:
            update(duration_seconds=round(time.monotonic()-start,1));self.events.pop(job['id'],None)

    def close(self):
        for event in list(self.events.values()):event.set()
        self.pool.shutdown(wait=True,cancel_futures=True)
