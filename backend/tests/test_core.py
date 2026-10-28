from __future__ import annotations
import json
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.analysis import inventory, permissions, compare, snapshot
from backend.core import Workbench, validate_path, review_packet
from backend.storage import Store


SOURCE='''from mcp.server.fastmcp import FastMCP
mcp=FastMCP("test")
@mcp.tool()
def read_report(path: str) -> str:
    """Reads a report."""
    return open(path).read()
'''


def test_ai_review_receives_bounded_saved_source_and_real_line_references():
    finding={'location':{'path':'server.py','range':{'start_line':8}}}
    source='\n'.join(f'line {i}' for i in range(1,100))
    packet=review_packet('scan',[finding]*12,{'server.py':source,'private.py':'must not be included'})
    assert len(packet['findings'])==10 and len(packet['sources'])==10
    for item in packet['sources']:
        assert item['path']=='server.py'
        assert item['range']['start_line']==4
        assert item['snippet'].splitlines()[0]=='line 4'
        assert item['range']['end_line']==19
        assert 'line 99' not in item['snippet']


def test_inventory_does_not_execute_target(tmp_path):
    marker=tmp_path/'should_not_exist'
    source=f'open({str(marker)!r}, "w").write("bad")\n'+SOURCE
    tools,warnings=inventory({'server.py':source})
    assert len(tools)==1 and not marker.exists()
    assert tools[0]['accesses']['filesystem.read'][0]['dynamic'] is True
    assert tools[0]['input_schema']['required']==['path']


def test_missing_declaration_and_observation_stay_unknown():
    tools,_=inventory({'server.py':SOURCE})
    rows=permissions(tools,{'server.py':SOURCE})
    assert all(row['declared'] is None and row['observed'] is None for row in rows)
    assert all(row['assessment']=='declaration_missing' for row in rows)
    assert all(row['observation_status']=='not_measured' for row in rows)


def test_known_static_mismatch_is_not_runtime_observation():
    src=SOURCE.replace('open(path)','open("private/payroll.txt")')
    files={'server.py':src,'sentinel.permissions.yaml':'version: 1\ntools:\n  read_report:\n    filesystem:\n      read:\n        scopes: ["public/**"]\n'}
    tools,_=inventory(files);rows=permissions(tools,files)
    read=next(x for x in rows if x['capability']=='filesystem.read')
    assert read['assessment']=='static_mismatch'
    assert read['observed'] is None
    assert read['inferred'][0]['evidence']['snippet']


def test_dynamic_target_is_unresolved_even_with_declared_scope():
    files={'server.py':SOURCE,'sentinel.permissions.yaml':'version: 1\ntools:\n  read_report:\n    filesystem:\n      read:\n        scopes: ["reports/**"]\n'}
    tools,_=inventory(files);row=permissions(tools,files)[0]
    assert row['assessment']=='unresolved'


def test_scope_path_outside_allowed_root_rejected(tmp_path):
    root=tmp_path/'allowed';root.mkdir();outside=tmp_path/'other';outside.mkdir()
    with pytest.raises(ValueError):validate_path(str(outside),[root])
    with pytest.raises(ValueError):validate_path('..',[root])


def test_snapshot_ignores_environment_and_keeps_source_hash(tmp_path):
    (tmp_path/'server.py').write_text(SOURCE)
    (tmp_path/'.venv').mkdir();(tmp_path/'.venv'/'secret.py').write_text('ignored')
    first=snapshot(tmp_path)
    assert set(first['files'])=={'server.py'}
    (tmp_path/'server.py').write_text(SOURCE+'\n# update\n')
    assert snapshot(tmp_path)['hash']!=first['hash']


def _scan(key,complete=True,findings=None):
    return {'id':key,'project_id':'p','profile':'rules_only','sentinel_version':'1.4.0','selected_rule_ids':['SENT-002'],'analysis_complete':complete,'findings':findings or [],'tools':[],'permissions':[]}


def test_incomplete_comparison_never_reports_resolved():
    finding={'dedup_key':'a','rule_id':'SENT-002','title':'unsafe','location':{'path':'a.py'}}
    result=compare(_scan('a',True,[finding]),_scan('b',False,[]))
    assert not result['comparable']
    assert not result['findings']['no_longer_observed']
    assert result['findings']['not_comparable']==[finding]


def test_rule_scope_change_prevents_resolution():
    before=_scan('a');after=_scan('b');after['selected_rule_ids']=[]
    assert compare(before,after)['comparable'] is False


def test_annotation_does_not_change_original_engine_report(tmp_path):
    wb=Workbench(tmp_path)
    try:
        raw={'findings':[{'finding_id':'f','status':'needs_review','title':'risk'}]}
        wb.store.put('scan',{'id':'s','status':'completed','findings':raw['findings'],'engine_report':raw})
        wb.annotate('s','f','false_positive','sample only')
        scan=wb.scan('s')
        assert scan['findings'][0]['annotation']['decision']=='false_positive'
        assert scan['engine_report']==raw
        assert scan['findings'][0]['status']=='needs_review'
    finally:wb.close()


def test_html_export_escapes_untrusted_metadata(tmp_path):
    wb=Workbench(tmp_path)
    try:
        raw={**_scan('s'),'project_name':'<script>alert(1)</script>','status':'completed','findings':[{'title':'<img src=x onerror=alert(1)>','remediation':'<script>x</script>'}]}
        output=wb.export_html(raw)
        assert '<script>' not in output and '<img src=x' not in output
        assert '&lt;script&gt;' in output
    finally:wb.close()


def test_store_recovery_marks_interrupted_job_failed(tmp_path):
    store=Store(tmp_path/'data.sqlite3')
    store.put('scan',{'id':'s','status':'running'})
    store.recover()
    assert store.get('scan','s')['status']=='failed'
    assert store.get('scan','s')['analysis_complete'] is False


def test_cancel_flag_is_only_for_own_job(tmp_path):
    wb=Workbench(tmp_path)
    try:
        wb.store.put('scan',{'id':'s','status':'running'})
        wb.cancel_events['s']=threading.Event()
        wb.cancel('s')
        assert wb.cancel_events['s'].is_set()
        assert wb.store.get('scan','s')['status']=='cancelling'
    finally:wb.close()


def test_stage_event_keeps_event_type_and_stage_name_distinct(tmp_path):
    wb=Workbench(tmp_path)
    try:
        wb.store.put('scan',{'id':'s','status':'running','stages':[{'name':'static','status':'pending'}]})
        wb._stage('s','static','running')
        event=wb.store.events('s')[0]
        assert event['type']=='stage'
        assert event['name']=='static'
        assert wb.store.get('scan','s')['stages'][0]['status']=='running'
    finally:wb.close()


@pytest.mark.parametrize('terminal', ['failed','cancelled'])
def test_terminated_job_cannot_leave_running_or_waiting_stages(tmp_path, terminal):
    wb=Workbench(tmp_path)
    try:
        wb.store.put('scan',{'id':'s','status':terminal,'stages':[
            {'name':'preparing','status':'succeeded'},
            {'name':'static','status':'running'},
            {'name':'inventory','status':'pending'}]})
        wb._finish_stages('s',terminal)
        statuses=[s['status'] for s in wb.store.get('scan','s')['stages']]
        assert statuses==['succeeded',terminal,'skipped']
    finally:wb.close()


def test_confirmed_annotation_requires_reason(tmp_path):
    wb=Workbench(tmp_path)
    try:
        wb.store.put('scan',{'id':'s','findings':[{'finding_id':'f'}]})
        with pytest.raises(ValueError,match='gerekçesi'):
            wb.annotate('s','f','confirmed','  ')
    finally:wb.close()


def test_settings_reject_literal_secrets(tmp_path):
    wb=Workbench(tmp_path)
    try:
        with pytest.raises(ValueError):wb.save_settings({'providers':{'api':{'api_key':'not-a-real-secret'}}})
        assert wb.save_settings({'providers':{'api':{'api_key_env':'TOOLLENS_API_KEY'}}})['providers']['api']['api_key_env']=='TOOLLENS_API_KEY'
    finally:wb.close()


def test_parser_failure_preserves_inventory_and_exports_honest_incomplete_report(tmp_path):
    wb=Workbench(tmp_path/'data')
    try:
        root=wb.roots[0]/'source';root.mkdir();(root/'server.py').write_text(SOURCE)
        project=wb.add_project('Parser boundary',str(root))
        wb.store.put('scan',{'id':'parse','project_id':project['id'],'project_name':project['name'],'profile':'rules_only','status':'queued','findings':[],'stages':[{'name':x,'status':'pending'} for x in ('preparing','static','inventory','ai','dynamic','reporting')]})
        wb.cancel_events['parse']=threading.Event()
        def failed_engine(*args,**kwargs):
            job=wb.data/'jobs'/'parse';job.mkdir(parents=True,exist_ok=True)
            (job/'stderr.log').write_text('PartialParsing: tests/a.ts; cannot parse TypeScript source')
            return 2
        with patch.object(wb,'_run_process',side_effect=failed_engine):wb._run('parse',project,'simple')
        result=wb.store.get('scan','parse')
        assert result['status']=='incomplete' and result['analysis_complete'] is False
        assert result['engine_report'] is None and result['findings']==[]
        assert result['tools'] and result['source_unchanged'] is True
        assert 'TypeScript' in result['error']
        report=wb.export_html(result)
        assert 'Sonuç için bilgi yetersiz' in report and 'TypeScript' in report
    finally:wb.close()
