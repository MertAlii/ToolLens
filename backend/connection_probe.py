"""Bounded, read-only MCP onboarding checks with stable public diagnoses."""
from __future__ import annotations
import asyncio
import os
import re
from time import monotonic
from urllib.parse import urlsplit
from .remote_mcp import discover
from .storage import now

DIAGNOSES = {
    'invalid_address': ('Adres kontrol edilmeli', 'HTTP veya HTTPS MCP bağlantı adresini girin. URL içinde kullanıcı bilgisi, anahtar, sorgu veya bölüm işareti bulunmamalı.', 'Sunucunun dokümantasyonundaki /mcp veya eski /sse adresini kopyalayın.'),
    'transport': ('Bağlantı türü geçersiz', 'Otomatik, Streamable HTTP veya SSE seçeneklerinden birini kullanın.', 'Emin değilseniz Otomatik algıla seçeneğini bırakın.'),
    'auth_variable': ('Anahtar değişkeni geçersiz', 'Gizli anahtarın kendisini değil, geçerli bir ortam değişkeninin adını girin.', 'Örneğin MCP_ACCESS_TOKEN adını kullanın; anahtarı bu forma yapıştırmayın.'),
    'auth_missing': ('Erişim anahtarı bulunamadı', 'Belirtilen ortam değişkeni ToolLens sunucu sürecinde tanımlı değil.', 'Değişkeni tanımlayıp ToolLens sunucusunu yeniden başlatın; sonra tekrar deneyin.'),
    'auth_rejected': ('Sunucu erişimi reddetti', 'Sunucu bu bağlantının erişim bilgilerini kabul etmedi.', 'Anahtarın geçerliliğini ve araç listeleme yetkisini kontrol edin. Etkileşimli OAuth girişi bu sürümde desteklenmiyor.'),
    'wrong_endpoint': ('MCP bağlantı adresi bulunamadı', 'Adres MCP oturumuna uygun yanıt vermedi. Normal web sayfası adresi yeterli değildir.', 'Tam /mcp veya eski /sse adresini ve seçilen bağlantı türünü kontrol edin.'),
    'dns': ('Sunucu adı çözümlenemedi', 'Sunucu adı ağ üzerinden bulunamadı.', 'Adresin yazımını, internet bağlantısını ve gerekiyorsa VPN bağlantısını kontrol edin.'),
    'offline': ('Sunucuya bağlanılamadı', 'Belirtilen sunucu veya port bağlantıyı kabul etmedi.', 'Sunucunun açık olduğunu, adresi ve portu kontrol edin.'),
    'timeout': ('Sunucu zamanında yanıt vermedi', 'MCP oturumu veya araç listesi süre sınırı içinde tamamlanamadı.', 'Sunucunun çalıştığını kontrol edip tekrar deneyin; uzun bekleme temiz sonuç değildir.'),
    'rate_limit': ('İstek sınırına ulaşıldı', 'Sunucu bu aşamada yeni istek kabul etmiyor.', 'Bir süre bekleyip tekrar deneyin.'),
    'server_error': ('Sunucu hata verdi', 'Sunucu MCP isteğini işlerken hata bildirdi.', 'Sunucunun durumunu veya yöneticisinin günlüğünü kontrol edin.'),
    'redirect': ('Yönlendirme durduruldu', 'Bağlantı başka bir sunucuya yönlendirildiği için oturum durduruldu.', 'Doğrudan resmi MCP uç noktasını kullanın. Anahtar başka sunucuya gönderilmedi.'),
    'restricted_address': ('Bu adres desteklenmiyor', 'Bağlantı adresi uygulamanın desteklediği ağ kapsamının dışında.', 'Uzak sunucularda HTTPS, bu bilgisayarda HTTP kullanın; sistem ve metadata adreslerini hedeflemeyin.'),
    'no_catalog': ('Araç listesi doğrulanamadı', 'Sunucu araç listeleme yeteneği yayımlamıyor veya eksiksiz ve tekil araç listesi veremedi.', 'Sunucunun MCP tools/list desteğini ve katalog sınırlarını kontrol edin.'),
    'protocol_version': ('MCP sürümü uyumlu değil', 'Adres doğru olabilir; sunucu ile istemci ortak bir MCP protokol sürümünde anlaşamadı.', 'Sunucunun desteklediği MCP sürümünü kontrol edin. Bu sonuç yanlış adres veya güvenli sunucu anlamına gelmez.'),
    'protocol': ('MCP oturumu tamamlanamadı', 'Bağlantıdan geçerli ve eksiksiz bir MCP araç listesi alınamadı.', 'MCP adresini, bağlantı türünü ve sunucunun güncel durumunu kontrol edin.'),
}

def _classify(message):
    value=message.casefold()
    if any(x in value for x in ('protokol sürüm','protocol version','unsupported protocol')):return 'protocol_version'
    if 'ortam değişkeni bulunamadı' in value:return 'auth_missing'
    if 'erişimi reddetti' in value:return 'auth_rejected'
    if 'başka bir sunucuya yönlendirildi' in value:return 'redirect'
    if 'çözümlenemedi' in value:return 'dns'
    if 'bağlanılamadı' in value:return 'offline'
    if any(x in value for x in ('zaman aşımı','25 saniye','süre sınır')):return 'timeout'
    if 'istek sınır' in value:return 'rate_limit'
    if 'sunucusu hata verdi' in value:return 'server_error'
    if any(x in value for x in ('yalnız bu bilgisayarda','uzak sunucular için https','bu ağ adresi','bu sistem adresi')):return 'restricted_address'
    if 'bağlantı ucu olarak' in value:return 'wrong_endpoint'
    if any(x in value for x in ('araç listeleme yeteneği','araç listesi','bir araç tanımı','en fazla 200')):return 'no_catalog'
    return 'protocol'

def _failure(code,started):
    title,message,next_step=DIAGNOSES[code]
    return {'status':'failed','checked_at':now(),'duration_seconds':round(monotonic()-started,2),
            'diagnosis':{'code':code,'title':title,'message':message,'next_step':next_step},
            'message':message,'next_step':next_step,'tool_count':None,'server_info':None}

async def probe(url,auth_env=None,transport='auto'):
    """Initialize and list tools only; no target tools or source files are read."""
    started=monotonic()
    try:
        parsed=urlsplit(url.strip())
        valid=parsed.scheme in ('http','https') and bool(parsed.hostname) and not (parsed.username or parsed.password or parsed.query or parsed.fragment)
        parsed.port
    except (ValueError,AttributeError):valid=False
    if not valid:return _failure('invalid_address',started)
    if transport not in ('auto','streamable_http','sse'):return _failure('transport',started)
    if auth_env:
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]{0,100}',auth_env):return _failure('auth_variable',started)
        if not os.environ.get(auth_env):return _failure('auth_missing',started)
    try:
        tools,server=await asyncio.wait_for(discover(url.strip(),auth_env,transport=transport),timeout=28)
        return {'status':'connected','checked_at':now(),'duration_seconds':round(monotonic()-started,2),
                'tool_count':len(tools),'server_info':server,'diagnosis':{'code':'connected','title':'MCP bağlantısı doğrulandı','message':'Sunucu ile MCP oturumu açıldı ve araç listesi alındı.','next_step':'Projeyi oluşturup araç tanımlarının incelemesine geçebilirsiniz.'},
                'scope':'contract_only','message':'Araç listesi alındı; kaynak kod veya araç davranışı incelenmedi.',
                'next_step':'Projeyi oluşturup araç tanımlarının incelemesine geçebilirsiniz.'}
    except asyncio.CancelledError:raise
    except TimeoutError:return _failure('timeout',started)
    except ValueError as exc:return _failure(_classify(str(exc)),started)
    except Exception:return _failure('protocol',started)
