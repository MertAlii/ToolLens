"""Source-only inventory and conservative permission interpretation; never imports targets."""
from __future__ import annotations

import ast
import fnmatch
import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlparse
import yaml

IGNORED = {'.git','.venv','venv','node_modules','__pycache__','.mypy_cache','.pytest_cache','dist','build'}
CAPABILITIES = ('filesystem.read','filesystem.write','network')


def source_files(root):
    root=Path(root).resolve()
    for directory,dirs,filenames in os.walk(root,followlinks=False):
        folder=Path(directory)
        dirs[:]=sorted(d for d in dirs if d not in IGNORED and not (folder/d).is_symlink() and not getattr(folder/d,'is_junction',lambda:False)())
        for filename in sorted(filenames):
            path=folder/filename
            if path.is_file() and not path.is_symlink() and path.resolve().is_relative_to(root):
                if path.suffix in ('.py','.ts','.mts','.cts','.yaml','.yml','.json','.toml') and path.stat().st_size <= 2_000_000:
                    yield path


def snapshot(root):
    files = {}
    digest = hashlib.sha256()
    total = 0
    for path in source_files(root):
        data = path.read_bytes()
        total += len(data)
        if total > 30_000_000:
            raise ValueError('Proje kaynak görüntüsü 30 MB sınırını aşıyor.')
        rel = path.relative_to(root).as_posix()
        digest.update(rel.encode()+b'\0'+data+b'\0')
        files[rel] = data.decode('utf-8', errors='replace')
    return {'hash':digest.hexdigest(),'files':files}


def name(node):
    if isinstance(node,ast.Name): return node.id
    if isinstance(node,ast.Attribute): return name(node.value)+'.'+node.attr
    return ''


def literal(node):
    if isinstance(node,ast.Constant) and isinstance(node.value,str): return node.value
    if isinstance(node,ast.Call) and name(node.func).split('.')[-1]=='Path' and node.args:
        return literal(node.args[0])
    return None


def _annotation(node):
    return ast.unparse(node) if node else 'Any'


def _type(annotation):
    text = annotation.lower()
    return 'integer' if text=='int' else 'number' if text=='float' else 'boolean' if text=='bool' else 'array' if 'list' in text else 'string'


def inventory(files):
    tools,warnings = [],[]
    for path,content in files.items():
        if not path.endswith('.py'): continue
        try: tree=ast.parse(content)
        except SyntaxError as exc:
            warnings.append({'code':'parse_error','message':f'{path}:{exc.lineno} çözümlenemedi.'});continue
        lines=content.splitlines()
        context_names={'Context'}
        aliases={}
        for imported in ast.walk(tree):
            if isinstance(imported,ast.ImportFrom) and imported.module:
                for alias in imported.names:
                    aliases[alias.asname or alias.name]=imported.module+'.'+alias.name
                    if alias.name=='Context' and imported.module.startswith(('mcp','fastmcp')):
                        context_names.add(alias.asname or alias.name)
            elif isinstance(imported,ast.Import):
                for alias in imported.names:aliases[alias.asname or alias.name]=alias.name
        for node in ast.walk(tree):
            if not isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
            decorators=[d for d in node.decorator_list if name(d.func if isinstance(d,ast.Call) else d).split('.')[-1] in ('tool','register_tool')]
            if not decorators:continue
            tool_name=node.name;description=ast.get_docstring(node) or ''
            for dec in decorators:
                if isinstance(dec,ast.Call):
                    for kw in dec.keywords:
                        if kw.arg=='name' and literal(kw.value):tool_name=literal(kw.value)
                        if kw.arg=='description' and literal(kw.value):description=literal(kw.value)
            positional=node.args.posonlyargs+node.args.args
            args=positional+node.args.kwonlyargs
            required_names={a.arg for a in positional[:len(positional)-len(node.args.defaults)]}
            required_names.update(a.arg for a,default in zip(node.args.kwonlyargs,node.args.kw_defaults) if default is None)
            args=[a for a in args if a.arg not in ('self','cls') and _annotation(a.annotation).strip("'\"").split('.')[-1] not in context_names]
            schema={'type':'object','properties':{a.arg:{'type':_type(_annotation(a.annotation))} for a in args},'required':[a.arg for a in args if a.arg in required_names]}
            accesses={k:[] for k in CAPABILITIES}
            for call in ast.walk(node):
                if not isinstance(call,ast.Call):continue
                call_name=name(call.func);cap=None;target=None
                prefix,*rest=call_name.split('.')
                call_name='.'.join([aliases.get(prefix,prefix),*rest])
                if call_name=='open' or call_name.endswith(('.read_text','.read_bytes','.write_text','.write_bytes','.open')):
                    mode=next((literal(x.value) for x in call.keywords if x.arg=='mode'),None)
                    if mode is None and len(call.args)>1:mode=literal(call.args[1])
                    cap='filesystem.write' if call_name.endswith(('.write_text','.write_bytes')) or mode and any(x in mode for x in 'wax+') else 'filesystem.read'
                    target=literal(call.args[0]) if call_name=='open' and call.args else literal(call.func.value) if isinstance(call.func,ast.Attribute) else None
                elif call_name in ('os.remove','os.unlink','os.rmdir','shutil.rmtree') or call_name.endswith(('.unlink','.rmdir')):
                    cap='filesystem.write'
                    target=literal(call.args[0]) if call_name in ('os.remove','os.unlink','os.rmdir','shutil.rmtree') and call.args else literal(call.func.value) if isinstance(call.func,ast.Attribute) else None
                elif call_name.startswith(('requests.','httpx.','urllib.request.','aiohttp.')) and call_name.split('.')[-1] in ('get','post','put','delete','request','urlopen','urlretrieve'):
                    cap='network';url=literal(call.args[0]) if call.args else None
                    if url:target=urlparse(url).netloc or url
                if cap:
                    accesses[cap].append({'target':target,'dynamic':target is None,'evidence':{'path':path,'start_line':call.lineno,'end_line':getattr(call,'end_lineno',call.lineno),'snippet':'\n'.join(lines[max(0,call.lineno-1):getattr(call,'end_lineno',call.lineno)])}})
            tools.append({'id':f'{path}:{tool_name}:{node.lineno}','name':tool_name,'description':description,'path':path,'start_line':node.lineno,'end_line':node.end_lineno,'input_schema':schema,'accesses':accesses,'recognition':'recognized','limitations':['Yalnız doğrudan tanınan Python araçları ve desteklenen çağrı biçimleri incelendi; helper akışları eksiksiz sayılmaz.']})
    if any(p.endswith(('.ts','.mts','.cts')) for p in files):
        warnings.append({'code':'typescript_inventory','message':'TypeScript araç envanteri için Sentinel kapsam kaydı esas alınır; yerel yetki çıkarımı Python ile sınırlıdır.'})
    return tools,warnings


def _declared(manifest,tool,cap):
    if not isinstance(manifest,dict) or not isinstance(manifest.get('tools'),dict) or tool not in manifest['tools']:return None
    value=manifest['tools'][tool]
    for part in cap.split('.'):
        if not isinstance(value,dict):return None
        value=value.get(part)
    if not isinstance(value,dict) or not isinstance(value.get('scopes',[]),list):return None
    return value.get('scopes',[])


def permissions(tools, files, runtime=None):
    manifest=None;issue=None
    if 'sentinel.permissions.yaml' in files:
        try:
            manifest=yaml.safe_load(files['sentinel.permissions.yaml'])
            if not isinstance(manifest,dict):issue='İzin beyanı nesne biçiminde değil.'
        except yaml.YAMLError:issue='İzin beyanı okunamadı.'
    rows=[]
    for tool in tools:
        for cap in CAPABILITIES:
            declared=_declared(manifest,tool['name'],cap)
            inferred=tool['accesses'][cap]
            unknown=any(x['dynamic'] for x in inferred)
            status='not_measured'
            if declared is None:status='declaration_missing'
            elif unknown:status='unresolved'
            elif any(not any(fnmatch.fnmatchcase(x['target'],scope) for scope in declared) for x in inferred):status='static_mismatch'
            elif inferred:status='no_static_mismatch_observed'
            elif declared:status='unresolved'
            row={'id':f"{tool['id']}:{cap}",'tool_id':tool['id'],'tool':tool['name'],'capability':cap,'declared':declared,'inferred':inferred,'observed':None,'observation_status':'not_measured','assessment':status,'evidence':([{'path':'sentinel.permissions.yaml','kind':'declaration'}] if declared is not None else [])+[x['evidence'] for x in inferred],'limitation':issue or 'Kod çıkarımı çalışma anında erişim kanıtı değildir. Desteklenmeyen akışlarda sonuç belirsizdir.'}
            rows.append(row)
    # Only a host-observed SENT-010 canary proves a file-write side effect here.
    # Generic logs, a successful tool response or a catalog entry are not telemetry.
    for finding in (runtime or {}).get('findings',[]):
        evidence=finding.get('evidence') or {}
        proof=evidence.get('proof') or {}
        effects=proof.get('effects') or {}
        if evidence.get('probe_id')!='SENT-010' or proof.get('verdict')!='violation_observed' or effects.get('canary_after') is not True:
            continue
        for row in rows:
            if row['tool']==proof.get('tool') and row['capability']=='filesystem.write':
                observation={'target':'/sentinel-scratch/sent-010-canary','kind':'host_observed_canary','probe_id':'SENT-010','attempt_id':evidence.get('attempt_id'),'evidence_id':finding.get('finding_id'),'effects':effects}
                row['observed']=[*(row['observed'] or []),observation]
                row['observation_status']='violation_observed'
                row['assessment']='runtime_violation'
                row['evidence'].append({'kind':'runtime','finding_id':finding.get('finding_id'),'probe_id':'SENT-010','attempt_id':evidence.get('attempt_id')})
                row['limitation']='Yalnız bu testte host tarafından gözlenen canary yazımı kanıtlandı; diğer dosya ve ağ erişimleri ölçülmedi.'
    return rows


def finding_identity(item):
    loc=item.get('location',{})
    return item.get('dedup_key') or json.dumps([item.get('rule_id'),loc.get('path'),item.get('title')],sort_keys=True)


def compare(before,after):
    compatible=before.get('project_id')==after.get('project_id') and before.get('profile')==after.get('profile') and before.get('sentinel_version')==after.get('sentinel_version') and before.get('selected_rule_ids')==after.get('selected_rule_ids')
    complete=bool(before.get('analysis_complete') and after.get('analysis_complete') and compatible)
    a={finding_identity(x):x for x in before.get('findings',[])};b={finding_identity(x):x for x in after.get('findings',[])}
    findings={'new':[b[k] for k in b.keys()-a.keys()],'persisting':[b[k] for k in b.keys()&a.keys()],'no_longer_observed':[a[k] for k in a.keys()-b.keys()] if complete else [],'not_comparable':[a[k] for k in a.keys()-b.keys()] if not complete else []}
    a_tools={(x['path'],x['name']):x for x in before.get('tools',[])};b_tools={(x['path'],x['name']):x for x in after.get('tools',[])}
    changes=[]
    for key in a_tools.keys()|b_tools.keys():
        old,new=a_tools.get(key),b_tools.get(key)
        fields=[field for field in ('description','input_schema') if old and new and old.get(field)!=new.get(field)]
        if not old or not new or fields:changes.append({'tool':key[1],'path':key[0],'kind':'added' if not old else 'no_longer_observed' if not new else 'changed','fields':fields,'before':old,'after':new,'uncertain':not complete})
    a_perms={(x['tool'],x['capability']):x for x in before.get('permissions',[])};b_perms={(x['tool'],x['capability']):x for x in after.get('permissions',[])}
    permission_changes=[]
    for key in a_perms.keys()|b_perms.keys():
        old,new=a_perms.get(key),b_perms.get(key)
        def meaningful(x):return {k:x.get(k) for k in ('declared','inferred','observed','assessment')} if x else None
        if meaningful(old)!=meaningful(new):permission_changes.append({'tool':key[0],'capability':key[1],'before':old,'after':new})
    return {'before_scan_id':before['id'],'after_scan_id':after['id'],'comparable':complete,'reason':None if complete else 'Aynı proje, motor, profil ve iki tamamlanmış analiz gerekir; kaybolan bulgu düzeltilmiş sayılmaz.','findings':findings,'tools':changes,'permissions':permission_changes}
