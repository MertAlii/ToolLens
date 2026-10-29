"""Run real rules-only scans; preserve incomplete/failed cases and raw reports."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
APP = ROOT.parent


def verify_manifest(name: str) -> dict:
    path = ROOT / (name + '.json')
    raw = path.read_bytes().replace(b'\r\n', b'\n')
    if hashlib.sha256(raw).hexdigest() != path.with_suffix('.sha256').read_text().strip():
        raise ValueError('Frozen manifest digest mismatch: ' + name)
    return json.loads(raw)


def source_digest(folder: Path) -> str:
    return hashlib.sha256((folder / 'server.py').read_bytes().replace(b'\r\n', b'\n')).hexdigest()


def run_case(case: dict, destination: Path, timeout: int) -> dict:
    folder = ROOT / case['path']
    if source_digest(folder) != case['source_sha256']:
        return {**case, 'outcome': 'invalid_input', 'error': 'Frozen source digest mismatch'}
    result_file = destination / (case['id'] + '.json')
    env = os.environ.copy()
    # Short writable path avoids native Windows Semgrep socket name length limits.
    temp = Path(os.environ.get('TOOLLENS_EVAL_TEMP', str(Path.home() / 'Documents' / 'Codex' / 'tl-tmp')))
    temp.mkdir(parents=True, exist_ok=True)
    env.update(TEMP=str(temp), TMP=str(temp), PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    command = [sys.executable, '-m', 'sentinel', 'scan', str(folder), '--rules-only', '--format', 'json', '--output', str(result_file)]
    started = time.monotonic()
    try:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                   encoding='utf-8', errors='replace', env=env, shell=False,
                                   creationflags=(subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP) if os.name == 'nt' else 0,
                                   start_new_session=os.name != 'nt')
        try:
            stdout, stderr = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'nt':
                subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'], capture_output=True, timeout=10, check=False)
            else:
                import signal
                os.killpg(process.pid, signal.SIGTERM)
            process.communicate(timeout=10)
            raise
        completed = subprocess.CompletedProcess(command, process.returncode, stdout, stderr)
        report = json.loads(result_file.read_text(encoding='utf-8')) if result_file.exists() else None
        status = 'complete' if completed.returncode in (0, 1) and report and report.get('analysisComplete') else 'incomplete' if completed.returncode == 3 else 'failed'
        rules = [item.get('rule_id') for item in (report or {}).get('findings', [])]
        present = case['target_rule'] in rules
        score = ('TP' if present else 'FN') if case['expected_target_present'] else ('FP' if present else 'TN')
        return {**case, 'outcome': status, 'exit_code': completed.returncode, 'duration_seconds': round(time.monotonic()-started, 3),
                'target_present': present if status == 'complete' else None, 'score': score if status == 'complete' else None,
                'observed_rule_ids': rules, 'additional_rule_ids': sorted(set(rules)-{case['target_rule']}),
                'stderr': completed.stderr[-4000:], 'report': result_file.name if result_file.exists() else None}
    except subprocess.TimeoutExpired:
        return {**case, 'outcome': 'timeout', 'duration_seconds': round(time.monotonic()-started, 3), 'score': None}
    except (OSError, ValueError) as error:
        return {**case, 'outcome': 'failed', 'error': str(error), 'score': None}


def version_measurements() -> list[dict]:
    sys.path.insert(0, str(APP))
    from backend.analysis import inventory, permissions
    rows = []
    for case in verify_manifest('version_manifest')['pairs']:
        sides = {}
        for side in ('before', 'after'):
            folder = ROOT / case['path'] / side
            files = {p.name: p.read_text(encoding='utf-8') for p in folder.iterdir() if p.is_file()}
            source = files['server.py']
            if hashlib.sha256(source.encode()).hexdigest() != case[side+'_sha256']: raise ValueError('Frozen version source changed')
            permissions_text = files.get('sentinel.permissions.yaml', '')
            if hashlib.sha256(permissions_text.encode()).hexdigest() != case[side+'_permissions_sha256']:
                raise ValueError('Frozen version declaration changed')
            tools, warnings = inventory(files)
            sides[side] = {'tools': tools, 'permissions': permissions(tools, files), 'warnings': warnings}
        a, b = sides['before']['tools'], sides['after']['tools']
        same_identity = len(a)==len(b)==1 and a[0]['name']==b[0]['name']
        dynamic_description = 'description_factory()' in (ROOT / case['path'] / 'after' / 'server.py').read_text()
        absent_manifest = not (ROOT / case['path'] / 'after' / 'sentinel.permissions.yaml').exists()
        observed = {'description_changed': bool(same_identity and a[0]['description'] != b[0]['description']),
                    'schema_changed': bool(same_identity and a[0]['input_schema'] != b[0]['input_schema']),
                    'permissions_changed': [x['declared'] for x in sides['before']['permissions']] != [x['declared'] for x in sides['after']['permissions']],
                    'uncertain': not same_identity or dynamic_description or absent_manifest}
        # This explicit evaluator keeps unresolved dynamic metadata visible even
        # when a product extractor currently returns an empty description.
        comparable_keys = [k for k in case['expected'] if k in observed]
        rows.append({**case, 'observed': observed, 'matches_expected': all(observed[k] == case['expected'][k] for k in comparable_keys),
                     'measurement': 'metadata extraction plus explicit ambiguity checks; not a security exploit verdict'})
    return rows


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument('--smoke', action='store_true', help='One vulnerable/fixed pair per family (12 cases)')
    parser.add_argument('--timeout', type=int, default=60)
    parser.add_argument('--jobs', type=int, choices=(1,2), default=2)
    args=parser.parse_args()
    manifest=verify_manifest('security_manifest')
    cases=[c for c in manifest['cases'] if not args.smoke or c['variant']==1]
    stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    destination=ROOT/'results'/stamp;destination.mkdir(parents=True,exist_ok=False)
    with ThreadPoolExecutor(max_workers=args.jobs) as pool:
        records=list(pool.map(lambda c: run_case(c,destination,args.timeout), cases))
    counts={key:sum(r.get('score')==key for r in records) for key in ('TP','TN','FP','FN')}
    completed=sum(r['outcome']=='complete' for r in records)
    tp,fp,fn=counts['TP'],counts['FP'],counts['FN']
    versions=version_measurements()
    summary={'created_at':stamp,'scope':'smoke' if args.smoke else 'full','requested':len(cases),'completed':completed,
             'non_completed':len(cases)-completed,'counts':counts,'precision':tp/(tp+fp) if tp+fp else None,'recall':tp/(tp+fn) if tp+fn else None,
             'denominator_note':'Precision/recall only use completed target-rule observations. Failures and additional findings retained separately.',
             'security_manifest_sha256':(ROOT/'security_manifest.sha256').read_text().strip(),
             'cases':records,'version_pairs':versions,'version_pairs_matching':sum(x['matches_expected'] for x in versions),
             'limitations':['Controlled small examples are not evidence of broad real-world accuracy.', 'No live model, vulnerable target execution or human participant study was performed.']}
    (destination/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines = ['# ToolLens kaynak değerlendirme sonucu', '',
             f'İstenen örnek: {len(cases)}. Tamamlanan: {completed}. Tamamlanmayan: {len(cases)-completed}.', '',
             '| Hedef kural sonucu | Sayı |', '| --- | --- |']
    lines += [f'| {key} | {counts[key]} |' for key in ('TP','TN','FP','FN')]
    lines += ['', 'Precision ve recall yalnız tamamlanmış hedef-kural gözlemlerini kapsar. Ek bulgular ham raporda ve JSON özetinde korunmuştur.', '',
              f'Metadata sürüm çiftleri: {len(versions)}; dondurulmuş beklentiyle eşleşen: {sum(x["matches_expected"] for x in versions)}.', '',
              'Bu sonuç denetimli küçük kaynak örneklerine aittir; gerçek dünya güvenlik doğruluğuna genellenmez. Canlı AI, riskli hedef yürütmesi veya insan katılımcı çalışması yapılmadı.']
    (destination/'SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (ROOT/'results'/'LATEST.txt').write_text(destination.name,encoding='ascii')
    print(json.dumps({k:summary[k] for k in ('scope','requested','completed','counts','precision','recall','version_pairs_matching')},ensure_ascii=False))
    print(destination)


if __name__=='__main__':main()
