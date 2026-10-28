"""Real loopback MCP protocol integration tests; discovery must never call tools."""
import asyncio
from contextlib import contextmanager
import json
import socket
import threading
import time

import pytest
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp import types
from starlette.responses import JSONResponse,RedirectResponse

from backend.remote_mcp import discover


@contextmanager
def live_mcp(mode='streamable_http',*,json_response=False,path=None,token=None,catalog=None,redirect=None,supports_tools=True):
    server=FastMCP('ToolLens protocol audit',json_response=json_response)
    calls=[];methods=[]
    @server.tool()
    def calculate(expression:str)->str:
        """Describe a calculation for the audit server."""
        calls.append(expression)
        return 'This should not execute during discovery'
    if catalog is not None:
        @server._mcp_server.list_tools()
        async def custom_catalog(request:types.ListToolsRequest)->types.ListToolsResult:
            return await catalog(request)
    if not supports_tools:server._mcp_server.request_handlers.pop(types.ListToolsRequest,None)
    if mode=='sse':
        server.settings.sse_path=path or '/sse';app=server.sse_app()
    else:
        server.settings.streamable_http_path=path or '/mcp';app=server.streamable_http_app()
    class AuditApp:
        async def __call__(self,scope,receive,send):
            if scope['type']=='http':
                if redirect:
                    await RedirectResponse(redirect,status_code=307)(scope,receive,send);return
                if token and dict(scope['headers']).get(b'authorization')!=('Bearer '+token).encode():
                    await JSONResponse({'error':'authorization required'},status_code=401)(scope,receive,send);return
                async def logged_receive():
                    message=await receive()
                    if message.get('body'):
                        try:methods.append(json.loads(message['body']).get('method'))
                        except (ValueError,AttributeError):pass
                    return message
                await app(scope,logged_receive,send)
            else:await app(scope,receive,send)
    listener=socket.socket();listener.bind(('127.0.0.1',0));port=listener.getsockname()[1]
    config=uvicorn.Config(AuditApp(),host='127.0.0.1',port=port,log_level='error',lifespan='on',timeout_graceful_shutdown=1)
    runner=uvicorn.Server(config);thread=threading.Thread(target=lambda:runner.run(sockets=[listener]),daemon=True);thread.start()
    deadline=time.monotonic()+8
    while not runner.started:
        if not thread.is_alive() or time.monotonic()>deadline:raise RuntimeError('Protocol test server did not start')
        time.sleep(.02)
    try:yield f'http://127.0.0.1:{port}'+(path or ('/sse' if mode=='sse' else '/mcp')),calls,methods
    finally:
        runner.should_exit=True;thread.join(4)
        if thread.is_alive():runner.force_exit=True;thread.join(2)
        listener.close()


@pytest.mark.parametrize('mode,json_response,path,expected',[
    ('streamable_http',False,None,'streamable_http'),
    ('streamable_http',True,None,'streamable_http'),
    ('sse',False,None,'sse'),
    ('sse',False,'/events','sse'),
])
def test_real_initialize_and_tools_list_across_http_transports(mode,json_response,path,expected):
    with live_mcp(mode,json_response=json_response,path=path) as (url,calls,methods):
        tools,info=asyncio.run(discover(url))
        assert [tool['name'] for tool in tools]==['calculate']
        assert info['name']=='ToolLens protocol audit' and info['transport']==expected
        assert 'initialize' in methods and 'tools/list' in methods
        assert 'tools/call' not in methods and calls==[]


def test_real_bearer_auth_and_readable_denial(monkeypatch):
    key='AUDIT_TEST_TOKEN_NOT_REAL';monkeypatch.setenv('TOOLLENS_AUDIT_TOKEN',key)
    with live_mcp(token=key) as (url,calls,methods):
        tools,_=asyncio.run(discover(url,auth_env='TOOLLENS_AUDIT_TOKEN'))
        assert len(tools)==1 and calls==[]
        with pytest.raises(ValueError,match='erişimi reddetti') as error:asyncio.run(discover(url))
        assert key not in str(error.value)


def test_real_pagination_is_complete_and_does_not_call_tools():
    cursors=[]
    async def catalog(request):
        cursor=request.params.cursor if request.params else None;cursors.append(cursor)
        return types.ListToolsResult(tools=[types.Tool(name='second' if cursor else 'first',inputSchema={'type':'object'})],nextCursor=None if cursor else 'page-2')
    with live_mcp(catalog=catalog) as (url,calls,methods):
        tools,_=asyncio.run(discover(url))
        assert [x['name'] for x in tools]==['first','second'] and cursors==[None,'page-2'] and calls==[]


def test_repeated_cursor_does_not_yield_false_complete_catalog():
    count=0
    async def catalog(request):
        nonlocal count;count+=1
        return types.ListToolsResult(tools=[types.Tool(name='tool_'+str(count),inputSchema={'type':'object'})],nextCursor='again')
    with live_mcp(catalog=catalog) as (url,_,__):
        with pytest.raises(ValueError,match='aynı sayfa imlecini'):asyncio.run(discover(url))


def test_over_limit_catalog_does_not_yield_truncated_success():
    async def catalog(request):return types.ListToolsResult(tools=[types.Tool(name='tool_'+str(i),inputSchema={'type':'object'}) for i in range(201)])
    with live_mcp(catalog=catalog) as (url,_,__):
        with pytest.raises(ValueError,match='en fazla 200'):asyncio.run(discover(url))


def test_real_waiting_connection_can_be_cancelled():
    async def catalog(request):
        await asyncio.sleep(30)
        return types.ListToolsResult(tools=[])
    event=threading.Event()
    with live_mcp(catalog=catalog) as (url,_,__):
        timer=threading.Timer(.3,event.set);timer.start();started=time.monotonic()
        try:
            with pytest.raises(InterruptedError,match='iptal'):asyncio.run(discover(url,cancel_event=event))
            assert time.monotonic()-started<4
        finally:timer.cancel()


def test_non_mcp_address_has_actionable_error():
    with live_mcp() as (url,_,__):
        with pytest.raises(ValueError,match='/mcp veya eski /sse'):asyncio.run(discover(url+'/wrong'))


def test_cross_origin_redirect_is_stopped_without_forwarding_bearer(monkeypatch):
    monkeypatch.setenv('TOOLLENS_AUDIT_TOKEN','AUDIT_TOKEN_DO_NOT_FORWARD')
    with live_mcp(redirect='http://127.0.0.1:1/other') as (url,_,__):
        with pytest.raises(ValueError,match='başka bir sunucuya'):asyncio.run(discover(url,auth_env='TOOLLENS_AUDIT_TOKEN'))


def test_server_without_tool_capability_does_not_get_clean_empty_catalog():
    with live_mcp(supports_tools=False) as (url,calls,methods):
        with pytest.raises(ValueError,match='araç listeleme yeteneği'):asyncio.run(discover(url))
        assert 'initialize' in methods and 'tools/list' not in methods and calls==[]
