import json
import os
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from backend import providers,credentials
from backend.api_catalog import PRESETS,prepare
from backend.static_worker import install_parse_probe

ANSWER={'content':'Bu kapsamda belirgin risk bulunmadı.','evidence_refs':[],'uncertainties':['Davranış testi yapılmadı.'],'patch':None}

@pytest.mark.parametrize('provider',list(PRESETS))
def test_presets_build_native_requests_and_validate_common_response(provider):
    preset=PRESETS[provider]
    response={'content':[{'type':'text','text':json.dumps(ANSWER)}]} if provider=='anthropic' else {'output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(ANSWER)}]}]} if provider=='openai' else {'choices':[{'message':{'content':json.dumps(ANSWER)}}]}
    with patch.dict(os.environ,{preset['api_key_env']:'TEST_KEY_NOT_REAL'}),patch.object(credentials,'read_key',return_value=None),patch.object(providers,'_http',return_value=response) as request:
        result=providers.generate(provider,'test-model','review',{'sources':[]},config={'base_url':'https://untrusted.invalid/v1'})
    assert result['provider']==provider and result['model']=='test-model'
    assert request.call_args.args[0].startswith(preset['base_url'])
    body=request.call_args.args[1]
    if provider=='anthropic':
        assert 'output_config' in body
        assert request.call_args.kwargs['extra_headers']['anthropic-version']=='2023-06-01'
    elif provider!='openai':assert body['response_format']['type']=='json_schema'

@pytest.mark.parametrize('provider',list(PRESETS))
def test_each_preset_reads_real_catalog_without_invented_models(provider):
    with patch.dict(os.environ,{PRESETS[provider]['api_key_env']:'TEST_KEY_NOT_REAL'}),patch.object(credentials,'read_key',return_value=None),patch.object(providers,'_http',return_value={'data':[{'id':'account-specific-model'}]}) as request:
        assert providers.get_models(provider)==['account-specific-model']
    assert request.call_args.args[0]==PRESETS[provider]['base_url']+'/models'

def test_custom_api_endpoint_is_explicit_and_credential_is_not_rebound(tmp_path,monkeypatch):
    monkeypatch.setattr(credentials,'ROOT',tmp_path)
    key='TEST_ONLY_KEY_12345'
    result=credentials.save_key('api',key,'https://first.example/v1')
    assert result['saved'] and key not in json.dumps(result)
    assert credentials.read_key('api','https://first.example/v1')==key
    assert credentials.read_key('api','https://other.example/v1') is None
    if os.name=='nt':assert key.encode() not in (tmp_path/'api.bin').read_bytes()

def test_cursor_tool_call_is_rejected_and_plain_result_is_parsed():
    with pytest.raises(providers.ProviderError):providers._extract_cli('cursor',json.dumps({'type':'tool_call','subtype':'started','tool_call':{'shellToolCall':{}}}))
    value,usage=providers._extract_cli('cursor',json.dumps({'type':'result','is_error':False,'result':json.dumps(ANSWER)}))
    assert json.loads(value)==ANSWER and usage is None

def test_subscription_environment_removes_cursor_api_key():
    with patch.dict(os.environ,{'CURSOR_API_KEY':'TEST_ONLY'}):assert 'CURSOR_API_KEY' not in providers._cli_env()

def test_parse_probe_retains_security_configs_and_all_syntax_errors(tmp_path):
    output=tmp_path/'results.json';calls=[]
    def run(command,*args,**kwargs):
        calls.append(command)
        payload={'results':[],'errors':[{'type':'Syntax error','path':'bad.ts'}]} if '--optimizations' in command else {'results':[{'check_id':'security-rule'}],'errors':[]}
        output.write_text(json.dumps(payload),encoding='utf-8');return SimpleNamespace(returncode=0)
    adapter=SimpleNamespace(subprocess=SimpleNamespace(run=run))
    install_parse_probe(adapter)
    adapter.subprocess.run(['semgrep','scan','--output',str(output),'--config','upstream/typescript_parse_gate.yaml','--config','security.yaml','large.ts'])
    assert len(calls)==2 and 'none' in calls[0]
    assert 'security.yaml' not in calls[0] and 'security.yaml' in calls[1]
    assert '--optimizations' not in calls[1]
    result=json.loads(output.read_text());assert result['errors'][0]['path']=='bad.ts'
    assert result['results'][0]['check_id']=='security-rule'
