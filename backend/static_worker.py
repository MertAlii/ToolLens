"""ToolLens-owned scan launcher; keeps upstream sources unchanged."""
import os
import json
import sys
from pathlib import Path


def install_parse_probe(adapter):
    """Separate the syntax probe from security rules; force actual parsing.

    The upstream $X + pattern-not:$X probe repeatedly compares large subtrees.
    A fixed identifier with prefilter optimizations disabled parses every file
    without materializing every subtree as a candidate match. Security rules
    keep their original configs and optimization settings.
    """
    original=adapter.subprocess.run
    probe=Path(__file__).parent/'rules'/'typescript_parse_gate.yaml'
    def run(command,*args,**kwargs):
        if not isinstance(command,list) or not any(str(v).endswith('typescript_parse_gate.yaml') for v in command):return original(command,*args,**kwargs)
        gate_configs=[];main=[];index=0
        while index<len(command):
            if command[index]=='--config':
                config=command[index+1]
                if str(config).endswith('typescript_parse_gate.yaml'):gate_configs.append(str(config))
                else:main.extend(('--config',config))
                index+=2
            else:main.append(command[index]);index+=1
        if not gate_configs:return original(command,*args,**kwargs)
        # Remove all security configs from the syntax-only invocation.
        syntax=[];index=0
        while index<len(main):
            if main[index]=='--config':index+=2
            else:syntax.append(main[index]);index+=1
        syntax.extend(('--config',str(probe),'--optimizations','none'))
        first=original(syntax,*args,**kwargs)
        output=Path(command[command.index('--output')+1])
        if first.returncode not in (0,1) or not output.exists():return first
        syntax_payload=json.loads(output.read_text(encoding='utf-8'))
        if syntax_payload.get('errors'):
            print('ToolLens syntax diagnostics: '+json.dumps([{'type':e.get('type'),'path':e.get('path')} for e in syntax_payload['errors']],ensure_ascii=False),file=sys.stderr)
        if '--config' not in main:return first
        second=original(main,*args,**kwargs)
        if second.returncode in (0,1) and output.exists():
            payload=json.loads(output.read_text(encoding='utf-8'))
            payload['errors']=[*syntax_payload.get('errors',[]),*payload.get('errors',[])]
            if payload['errors']:
                print('ToolLens rule diagnostics: '+json.dumps([{'type':e.get('type'),'path':e.get('path')} for e in payload['errors']],ensure_ascii=False),file=sys.stderr)
            # Syntax probe matches are intentionally not security findings.
            output.write_text(json.dumps(payload),encoding='utf-8')
        return second
    adapter.subprocess.run=run

def main():
    from sentinel.static import semgrep_adapter
    # Per-rule budget. Never disable a rule or hide a scan timeout.
    semgrep_adapter.SEMGREP_TIMEOUT_SECONDS=max(10,min(60,int(os.environ.get('TOOLLENS_RULE_TIMEOUT','30'))))
    install_parse_probe(semgrep_adapter)
    from sentinel.cli import app
    app()

if __name__=='__main__':main()
