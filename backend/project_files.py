"""Project-scoped, read-only files and explicitly selected AI evidence."""
from pathlib import Path, PurePosixPath
import hashlib
import os
import re

IGNORED={'.git','.svn','.venv','venv','node_modules','__pycache__','.pytest_cache','dist','build','.next','.idea','.vscode'}
TEXT={'.py','.pyi','.ts','.tsx','.mts','.cts','.js','.jsx','.mjs','.cjs','.json','.yaml','.yml','.toml','.md','.txt','.html','.css','.scss','.sql','.sh','.ps1','.rs','.go','.java','.c','.h','.cpp','.vue','.svelte','.xml','.ini','.cfg','.csv','.ipynb'}
MAX_PREVIEW=512_000
MAX_CONTEXT=30_000
MAX_FILES=6
MENTIONS=re.compile(r'(?<![\w@])@(?:\{([^}\r\n]+)\}|([^\s@{}]+))')


def hidden(name):
    return name.startswith('.') or name in IGNORED or name.lower() in ('auth.json','credentials.json','credentials','id_rsa','id_ed25519') or Path(name).suffix.lower() in ('.pem','.key','.p12','.pfx')


def safe_path(root,relative='',directory=None):
    root=Path(root).resolve(strict=True)
    if '\\' in relative or ':' in relative or '\x00' in relative:
        raise ValueError('Proje içindeki göreli dosya konumunu kullanın.')
    rel=PurePosixPath(relative)
    if rel.is_absolute() or any(part in ('..','') or hidden(part) for part in rel.parts):
        raise ValueError('Bu konuma proje önizlemesinden erişilemez.')
    path=root
    for part in rel.parts:
        path=path/part
        if path.is_symlink() or getattr(path,'is_junction',lambda:False)():
            raise ValueError('Bağlantılı dosya ve klasörler önizlenmez.')
    try:resolved=path.resolve(strict=True)
    except FileNotFoundError:raise ValueError('Dosya veya klasör artık bulunamıyor. Dosya ağacını yenileyin.') from None
    if not resolved.is_relative_to(root):raise ValueError('Dosya proje klasörünün dışında.')
    if directory is True and not resolved.is_dir():raise ValueError('Klasör bekleniyor.')
    if directory is False and not resolved.is_file():raise ValueError('Dosya bekleniyor.')
    return resolved


def previewable(path):
    return path.suffix.lower() in TEXT or path.name in ('Dockerfile','Makefile','LICENSE','requirements.txt')


def tree(root,relative=''):
    folder=safe_path(root,relative,directory=True)
    rows=[]
    for path in folder.iterdir():
        if hidden(path.name) or path.is_symlink() or getattr(path,'is_junction',lambda:False)():continue
        try:
            if not path.is_dir() and not path.is_file():continue
            rows.append({'name':path.name,'path':path.relative_to(root).as_posix(),'kind':'folder' if path.is_dir() else 'file','size':0 if path.is_dir() else path.stat().st_size,'previewable':path.is_file() and previewable(path) and path.stat().st_size<=MAX_PREVIEW})
        except OSError:continue
    rows.sort(key=lambda p:(p['kind']!='folder',p['name'].casefold()))
    return {'path':relative,'entries':rows[:500],'truncated':len(rows)>500}


def index(root):
    result=[];visited=0;truncated=False
    for directory,dirs,files in os.walk(root,followlinks=False):
        visited+=1
        if visited>500:truncated=True;break
        folder=Path(directory)
        dirs[:]=sorted(d for d in dirs if not hidden(d) and not (folder/d).is_symlink() and not getattr(folder/d,'is_junction',lambda:False)())
        for name in sorted(files):
            path=folder/name
            if hidden(name) or path.is_symlink() or not previewable(path):continue
            try:
                if not path.is_file() or path.stat().st_size>MAX_PREVIEW:continue
                result.append({'path':path.relative_to(root).as_posix(),'size':path.stat().st_size})
            except OSError:continue
            if len(result)>=2000:truncated=True;break
        if truncated:break
    return {'files':result,'truncated':truncated}


def read_file(root,relative):
    path=safe_path(root,relative,directory=False)
    if not previewable(path):raise ValueError('Bu dosya türü metin önizlemesini desteklemiyor.')
    with path.open('rb') as f:
        before=os.fstat(f.fileno())
        data=f.read(MAX_PREVIEW+1)
        after=os.fstat(f.fileno())
    checked=safe_path(root,relative,directory=False)
    current=checked.stat()
    if checked!=path or (before.st_dev,before.st_ino,before.st_mtime_ns,before.st_size)!=(after.st_dev,after.st_ino,after.st_mtime_ns,after.st_size) or (current.st_dev,current.st_ino)!=(after.st_dev,after.st_ino):
        raise ValueError('Dosya okunurken değişti. Önizlemeyi yenileyip tekrar deneyin.')
    if len(data)>MAX_PREVIEW:raise ValueError('Önizleme 512 KB ile sınırlıdır.')
    if b'\x00' in data:raise ValueError('İkili dosyalar kod olarak önizlenmez.')
    try:content=data.decode('utf-8-sig')
    except UnicodeDecodeError:raise ValueError('Bu dosya UTF-8 metin biçiminde değil.') from None
    return {'path':relative,'content':content,'hash':hashlib.sha256(data).hexdigest(),'size':len(data),'line_count':max(1,len(content.splitlines()))}


def resolve_paths(question,selected,allow_empty=False):
    paths=list(selected)
    for match in MENTIONS.finditer(question):
        path=match.group(1) or match.group(2)
        if not match.group(1):path=path.rstrip('.,;!?`')
        if path not in paths:paths.append(path)
    paths=list(dict.fromkeys(paths))
    if not paths and not allow_empty:raise ValueError('Soruya @ ile en az bir dosya ekleyin.')
    if len(paths)>MAX_FILES:raise ValueError('Bir soruda en fazla 6 dosya kullanılabilir.')
    return paths


def evidence_chunks(file):
    # All selected content is supplied, in bounded strings. No silent clipping by
    # the model transport; a very long single line is sent as numbered fragments.
    chunks=[];buffer=[];start=1;length=0
    for number,line in enumerate(file['content'].splitlines() or [''],1):
        if buffer and length+len(line)+1>5000:
            chunks.append({'path':file['path'],'range':{'start_line':start,'end_line':number-1},'snippet':'\n'.join(buffer)})
            buffer=[];length=0
        if len(line)>5000:
            for offset in range(0,len(line),5000):
                chunks.append({'path':file['path'],'range':{'start_line':number,'end_line':number},'snippet':line[offset:offset+5000],'line_fragment':offset//5000+1})
            start=number+1
        else:
            if not buffer:start=number
            buffer.append(line);length+=len(line)+1
    if buffer:chunks.append({'path':file['path'],'range':{'start_line':start,'end_line':file['line_count']},'snippet':'\n'.join(buffer)})
    return chunks


def prepare_question(root,question,selected,allow_empty=False):
    paths=resolve_paths(question,selected,allow_empty=allow_empty)
    files=[read_file(root,path) for path in paths]
    if sum(f['size'] for f in files)>MAX_CONTEXT:
        raise ValueError('Seçilen dosyalar 30 KB AI bağlamı sınırını aşıyor. Daha az veya daha küçük dosya seçin; içerik sessizce kesilmez.')
    return files,{'question':question,'scope':'Yalnız kullanıcının seçtiği dosyaların bu soruya ait kopyaları. Projenin kalan dosyaları okunmadı; kod çalıştırılmadı.','sources':[chunk for f in files for chunk in evidence_chunks(f)]}
