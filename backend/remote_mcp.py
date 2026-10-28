"""Read-only MCP protocol inspection: initialize and tools/list, never tools/call."""
import asyncio
import hashlib
import ipaddress
import json
import os
import re
import socket
from datetime import timedelta
from urllib.parse import urlsplit,urlunsplit
from uuid import uuid4


def validate_endpoint(raw):
    p=urlsplit(raw.strip())
    if p.scheme not in ('http','https') or not p.hostname or p.username or p.password or p.query or p.fragment:
        raise ValueError('HTTP veya HTTPS MCP adresi girin. Gizli anahtarları URL içine yazmayın.')
    try:port=p.port
    except ValueError:raise ValueError('Bağlantı portu geçersiz.') from None
    if p.scheme=='http' and p.hostname not in ('localhost','127.0.0.1','::1'):
        raise ValueError('Uzak sunucular için HTTPS gerekir. HTTP yalnız bu bilgisayarda kullanılabilir.')
    if p.hostname.lower() in ('metadata.google.internal','metadata'):
        raise ValueError('Bu sistem adresi MCP hedefi olarak kullanılamaz.')
    try:addresses=socket.getaddrinfo(p.hostname,port or (443 if p.scheme=='https' else 80),type=socket.SOCK_STREAM)
    except OSError:raise ValueError('Sunucu adresi çözümlenemedi.') from None
    for item in addresses:
        addr=ipaddress.ip_address(item[4][0])
        if addr.is_link_local or addr.is_multicast or addr.is_unspecified or (addr.is_reserved and not addr.is_loopback):
            raise ValueError('Bu ağ adresi MCP hedefi olarak kullanılamaz.')
    return urlunsplit((p.scheme,p.netloc,p.path or '/','',''))


def _error_leaves(error):
    children=getattr(error,'exceptions',None)
    return [leaf for child in children for leaf in _error_leaves(child)] if children else [error]


def _http_status(error):
    for leaf in _error_leaves(error):
        response=getattr(leaf,'response',None)
        if response is not None:return response.status_code
    return None


def _connection_error(error):
    import httpx
    leaves=_error_leaves(error);status=_http_status(error)
    if any(isinstance(leaf,RuntimeError) and str(leaf).startswith('Unsupported protocol version from the server:') for leaf in leaves):return 'MCP protokol sürümü uyumsuz. Sunucu ile istemci ortak bir sürümde anlaşamadı; adres doğru olabilir.'
    if status in (401,403):return 'MCP sunucusu erişimi reddetti. Gerekliyse erişim anahtarının ortam değişkenini tanımlayın ve yetkisini kontrol edin.'
    if status in (404,405,406,415):return 'Adres bir MCP bağlantı ucu olarak yanıt vermedi. Sunucunun /mcp veya eski /sse bağlantı adresini kullanın; web ana sayfası yeterli değildir.'
    if status==429:return 'MCP sunucusunun istek sınırına ulaşıldı. Bir süre sonra yeniden deneyin.'
    if status and status>=500:return 'MCP sunucusu hata verdi. Sunucunun çalıştığını ve kontrol günlüğünü inceleyin.'
    if any(isinstance(e,httpx.ConnectError) for e in leaves):return 'MCP sunucusuna bağlanılamadı. Adresi, portu ve sunucunun çalıştığını kontrol edin.'
    if any(isinstance(e,(httpx.TimeoutException,TimeoutError)) for e in leaves):return 'MCP sunucusunun yanıtı zaman aşımına uğradı. Sunucuyu ve bağlantı adresini kontrol edin.'
    for leaf in leaves:
        if isinstance(leaf,ValueError) and str(leaf).startswith(('Bir araç','Bu sürüm','Araç listesi','MCP bağlantısı')):return str(leaf)
    return 'MCP protokol oturumu tamamlanamadı. Sunucunun /mcp veya eski /sse bağlantı adresini ve sunucu günlüğünü kontrol edin.'


async def discover(url,auth_env=None,cancel_event=None,transport='auto'):
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.client.sse import sse_client
    from mcp import ClientSession
    import httpx
    url=validate_endpoint(url)
    if transport not in ('auto','streamable_http','sse'):raise ValueError('MCP taşıma türü auto, streamable_http veya sse olmalı.')
    headers={}
    if auth_env:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,100}',auth_env):raise ValueError('Geçerli bir ortam değişkeni adı girin.')
        token=os.environ.get(auth_env)
        if not token:raise ValueError('MCP erişim anahtarının ortam değişkeni bulunamadı.')
        headers['Authorization']='Bearer '+token
    def origin(value):
        parsed=urlsplit(str(value));return parsed.scheme,parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80)
    expected_origin=origin(url)
    async def guard(request):
        # Same-origin slash redirects and legacy SSE POST session URLs are valid.
        # No redirect or server-supplied endpoint may send credentials elsewhere.
        if origin(request.url)!=expected_origin:raise ValueError('MCP bağlantısı başka bir sunucuya yönlendirildi; güvenlik için durduruldu.')
    def http_client(headers=None,timeout=None,auth=None):
        return httpx.AsyncClient(headers=headers,timeout=timeout or 8,auth=auth,follow_redirects=True,event_hooks={'request':[guard]})
    async def read_catalog(mode):
        manager=sse_client(url,headers=headers,timeout=8,sse_read_timeout=12,httpx_client_factory=http_client) if mode=='sse' else streamablehttp_client(url,headers=headers,timeout=8,sse_read_timeout=12,httpx_client_factory=http_client)
        async with manager as streams:
            read,write=streams[:2]
            async with ClientSession(read,write,read_timeout_seconds=timedelta(seconds=12)) as client:
                initialized=await client.initialize()
                if initialized.capabilities.tools is None:raise ValueError('MCP bağlantısı kuruldu ancak sunucu araç listeleme yeteneği yayımlamıyor. Bu sunucu için araç güvenliği sonucu üretilemez.')
                tools=[];cursor=None;seen_cursors=set();names=set()
                for _ in range(10):
                    if cancel_event is not None and cancel_event.is_set():raise InterruptedError('Kontrol iptal edildi.')
                    page=await client.list_tools(cursor=cursor)
                    for t in page.tools:
                        raw=t.model_dump(mode='json')
                        if len(json.dumps(raw).encode())>100_000:raise ValueError('Bir araç tanımı izin verilen boyutu aşıyor.')
                        if raw['name'] in names:raise ValueError('Araç listesi aynı araç adını birden çok kez içeriyor; eksiksiz ve tekil katalog doğrulanamadı.')
                        names.add(raw['name']);tools.append(raw)
                        if len(tools)>200:raise ValueError('Bu sürüm bir bağlantıda en fazla 200 araç tanımını inceler.')
                    cursor=page.nextCursor
                    if not cursor:
                        info=initialized.serverInfo.model_dump(mode='json');info['transport']=mode;info['protocol_version']=initialized.protocolVersion;info['discovery_method']='initialize/tools/list'
                        return tools,info
                    if cursor in seen_cursors:raise ValueError('Araç listesi aynı sayfa imlecini tekrarladı; eksiksiz sonuç üretilemedi.')
                    seen_cursors.add(cursor)
                raise ValueError('Araç listesi sayfa sınırını aştı; eksiksiz sonuç üretilemedi.')
    async def connect():
        first='sse' if transport=='auto' and urlsplit(url).path.rstrip('/').endswith('/sse') else 'streamable_http' if transport=='auto' else transport
        try:return await read_catalog(first)
        except Exception as error:
            # A legacy SSE GET endpoint normally returns 405 to the Streamable
            # HTTP initialize POST. Do not retry authentication or server errors.
            if transport=='auto' and first=='streamable_http' and _http_status(error) in (404,405,406,415):
                return await read_catalog('sse')
            raise
    task=asyncio.create_task(connect())
    try:
        deadline=asyncio.get_running_loop().time()+25
        while not task.done():
            if cancel_event is not None and cancel_event.is_set():
                task.cancel();raise InterruptedError('Kontrol iptal edildi.')
            if asyncio.get_running_loop().time()>deadline:
                task.cancel();raise ValueError('Sunucu 25 saniye içinde araç listesini vermedi. Adresi, oturumu ve HTTP MCP desteğini kontrol edin.')
            await asyncio.wait({task},timeout=.15)
        try:return await task
        except InterruptedError:raise
        except Exception as error:raise ValueError(_connection_error(error)) from None
    finally:
        if not task.done():task.cancel()
        await asyncio.gather(task,return_exceptions=True)


def analyze_catalog(raw_tools):
    tools=[];findings=[];permissions=[]
    for raw in raw_tools:
        name=raw['name'];description=raw.get('description') or ''
        path='mcp-tools/'+name+'.json'
        schema=raw.get('inputSchema') or {}
        tool={'id':hashlib.sha256(name.encode()).hexdigest()[:20],'name':name,'description':description,'path':path,'input_schema':schema,'annotations':raw.get('annotations'),'source_kind':'remote_contract'}
        tools.append(tool)
        def finding(rule,title,description_text):
            findings.append({'finding_id':str(uuid4()),'rule_id':rule,'title':title,'description':description_text,'remediation':'Araç tanımını ve sunucunun dokümantasyonunu doğrulayın. Bu kayıt davranışsal ihlal kanıtı değildir.','severity':'Medium','impact':'Medium','source':'remote_contract','location':{'kind':'logical','path':path,'range':{'start_line':1,'end_line':1}},'evidence':{'kind':'contract','snippet':json.dumps(raw,ensure_ascii=False,indent=2)},'status':'needs_review'})
        if re.search(r'ignore (?:all |previous |prior )?(?:instructions|rules)|system prompt|disregard|önceki talimatları|talimatları yok say',description,re.I):
            finding('TL-R001','Araç açıklaması yapay zekâyı yönlendirmeye çalışıyor olabilir','Araç açıklamasında işlev tanımı dışında talimat benzeri bir ifade var. Açıklama tek başına saldırı gerçekleştiğini göstermez.')
        if schema.get('type')!='object':
            finding('TL-R002','Aracın beklediği girdi biçimi açık değil','Yayımlanan girdi şemasında üst düzey nesne türü bulunmuyor. Sunucunun girdi sözleşmesi ayrıca incelenmeli.')
        for cap in ('filesystem.read','filesystem.write','network'):
            permissions.append({'id':tool['id']+':'+cap,'tool_id':tool['id'],'tool':name,'capability':cap,'declared':None,'inferred':[],'observed':None,'observation_status':'not_measured','assessment':'not_measured','static_status':'not_available','evidence':[{'path':path,'kind':'remote_contract','snippet':description}],'limitation':'Kaynak kodu ve erişim telemetrisi paylaşılmadı. Araç listesi gerçek bir MCP oturumundan alındı; dosya veya ağ davranışı ölçülmedi.'})
    return tools,findings,permissions
