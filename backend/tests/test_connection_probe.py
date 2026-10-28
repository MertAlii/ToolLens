"""Connection onboarding checks: public diagnoses, no tool execution or secrets."""
import asyncio
import json
from unittest.mock import AsyncMock,patch
import pytest
from backend.connection_probe import probe
from test_remote_mcp_protocol import live_mcp

@pytest.mark.parametrize('url',['not an address','https://user:password@example.test/mcp','https://example.test/mcp?key=SECRET','https://example.test/mcp#fragment','https://example.test:wrong/mcp'])
def test_malformed_or_secret_bearing_address_never_connects(url):
    with patch('backend.connection_probe.discover',new_callable=AsyncMock) as discovery:
        result=asyncio.run(probe(url))
    discovery.assert_not_called()
    assert result['status']=='failed' and result['diagnosis']['code']=='invalid_address'
    assert 'SECRET' not in json.dumps(result) and 'password' not in json.dumps(result)

def test_missing_key_is_detected_before_network_and_value_is_never_exposed(monkeypatch):
    monkeypatch.delenv('TOOLLENS_TEST_MISSING',raising=False)
    with patch('backend.connection_probe.discover',new_callable=AsyncMock) as discovery:
        result=asyncio.run(probe('http://127.0.0.1:9/mcp','TOOLLENS_TEST_MISSING'))
    discovery.assert_not_called()
    assert result['diagnosis']['code']=='auth_missing' and result['tool_count'] is None

@pytest.mark.parametrize('message,expected',[
    ('MCP sunucusuna bağlanılamadı.','offline'),
    ('Adres bir MCP bağlantı ucu olarak yanıt vermedi.','wrong_endpoint'),
    ('MCP sunucusu erişimi reddetti.','auth_rejected'),
    ('Sunucu adresi çözümlenemedi.','dns'),
    ('MCP sunucusunun yanıtı zaman aşımına uğradı.','timeout'),
    ('MCP sunucusunun istek sınırına ulaşıldı.','rate_limit'),
    ('MCP bağlantısı başka bir sunucuya yönlendirildi; güvenlik için durduruldu.','redirect'),
    ('MCP protokol sürümü uyumsuz.','protocol_version'),
    ('HTTP yalnız bu bilgisayarda kullanılabilir.','restricted_address'),
])
def test_trusted_connection_failures_are_actionable(message,expected):
    with patch('backend.connection_probe.discover',new_callable=AsyncMock,side_effect=ValueError(message)):
        result=asyncio.run(probe('http://127.0.0.1:9/mcp'))
    assert result['diagnosis']['code']==expected and result['next_step']
    assert result['server_info'] is None and result['tool_count'] is None

def test_unexpected_error_does_not_leak_underlying_credentials():
    with patch('backend.connection_probe.discover',new_callable=AsyncMock,side_effect=RuntimeError('PRIVATE_AUTH_TOKEN=SECRET')):
        result=asyncio.run(probe('http://127.0.0.1:9/mcp'))
    assert result['diagnosis']['code']=='protocol'
    assert 'SECRET' not in json.dumps(result) and 'PRIVATE_AUTH' not in json.dumps(result)

@pytest.mark.parametrize('mode',['streamable_http','sse'])
def test_real_onboarding_handshake_lists_tools_without_calling_them(mode):
    with live_mcp(mode) as (url,calls,methods):
        result=asyncio.run(probe(url,transport='auto'))
    assert result['status']=='connected' and result['tool_count']==1
    assert result['server_info']['transport']==mode
    assert result['scope']=='contract_only'
    assert calls==[] and 'tools/list' in methods and 'tools/call' not in methods

def test_real_auth_rejection_keeps_token_out_of_diagnosis(monkeypatch):
    monkeypatch.setenv('TOOLLENS_WIZARD_TEST_KEY','WRONG_SECRET_VALUE')
    with live_mcp(token='ACTUAL_SECRET_VALUE') as (url,calls,_):
        result=asyncio.run(probe(url,'TOOLLENS_WIZARD_TEST_KEY'))
    assert result['diagnosis']['code']=='auth_rejected'
    assert 'SECRET_VALUE' not in json.dumps(result) and calls==[]


def test_sdk_protocol_mismatch_remains_explicit_after_wrapper():
    from backend.remote_mcp import _connection_error
    from backend.connection_probe import _classify
    message=_connection_error(ExceptionGroup('connection',[RuntimeError('Unsupported protocol version from the server: unknown-version')]))
    assert _classify(message)=='protocol_version' and 'adres doğru olabilir' in message
