"""Disposable runtime process. Only launches target in Sentinel Docker sandboxes."""
from __future__ import annotations
import json
import sys
import os
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from uuid import UUID


def docker_command(command):
    from .environment import docker_environment
    from sentinel.errors import InfrastructureError
    try:
        return subprocess.run(command,check=False,capture_output=True,text=True,encoding='utf-8',errors='replace',env=docker_environment(),timeout=10 if len(command)>1 and command[1] in {'exec','inspect','kill','rm'} else 180,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    except (OSError,subprocess.TimeoutExpired) as exc:raise InfrastructureError(f'Docker işlemi tamamlanamadı: {exc}') from exc


def main():
    from sentinel.config import load_configuration
    from sentinel.dynamic.prober import run_dynamic_scan
    from sentinel.dynamic.sandbox import DockerSandbox
    from sentinel.finding import Finding
    root,report_file,output=map(Path,sys.argv[1:4])
    report=json.loads(report_file.read_text(encoding='utf-8'))
    cfg=load_configuration(root,cli_overrides={'rules_only':False},static_only=False)
    findings=tuple(Finding.model_validate_json(json.dumps({k:v for k,v in x.items() if k not in ('severity','review_disagrees')})) for x in report['findings'])
    result=run_dynamic_scan(DockerSandbox(cfg,UUID(report['scan_id']),runner=docker_command),findings,scan_id=UUID(report['scan_id']),timestamp=datetime.now(timezone.utc))
    payload={'complete':result.complete,'execution_successful':result.execution_successful,'findings':[x.model_dump(mode='json') for x in result.findings],'summary':result.summary.model_dump(mode='json'),'warnings':[x.model_dump(mode='json') for x in result.warnings]}
    output.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')


if __name__=='__main__':main()
