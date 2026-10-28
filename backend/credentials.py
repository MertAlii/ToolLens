"""API keys encrypted for the current Windows user; never stored in settings."""
from __future__ import annotations
import ctypes
import os
import re
import threading
from pathlib import Path

ROOT=Path(os.environ.get('TOOL_LENS_DATA',str(Path(__file__).resolve().parents[1]/'data')))/'credentials'
_memory={}
_lock=threading.RLock()

class Blob(ctypes.Structure):
    _fields_=[('size',ctypes.c_ulong),('data',ctypes.POINTER(ctypes.c_ubyte))]

def _crypt(data,decrypt=False):
    source=ctypes.create_string_buffer(data)
    input_blob=Blob(len(data),ctypes.cast(source,ctypes.POINTER(ctypes.c_ubyte)));output=Blob()
    function=ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    if not function(ctypes.byref(input_blob),None,None,None,None,1,ctypes.byref(output)):
        raise ValueError('API anahtarı Windows kullanıcı şifrelemesiyle işlenemedi.')
    try:return ctypes.string_at(output.data,output.size)
    finally:ctypes.windll.kernel32.LocalFree(output.data)

def _path(provider):
    if not re.fullmatch('[a-z_]{1,30}',provider):raise ValueError('Geçersiz bağlantı.')
    return ROOT/(provider+'.bin')

def save_key(provider,key,origin):
    if not isinstance(key,str) or not 8<=len(key.strip())<=4096 or any(c in key for c in '\r\n\x00'):raise ValueError('Geçerli bir API anahtarı girin.')
    import json
    payload=json.dumps({'key':key.strip(),'origin':origin},ensure_ascii=False).encode()
    with _lock:
        if os.name=='nt':
            ROOT.mkdir(parents=True,exist_ok=True);path=_path(provider);temporary=path.with_suffix('.tmp');temporary.write_bytes(_crypt(payload));os.replace(temporary,path)
        else:_memory[provider]=payload
    return {'saved':True,'storage':'windows_user_encrypted' if os.name=='nt' else 'session_only'}

def read_key(provider,origin):
    import json
    with _lock:
        try:
            raw=_crypt(_path(provider).read_bytes(),True) if os.name=='nt' else _memory.get(provider)
            value=json.loads(raw) if raw else {}
            return value.get('key') if value.get('origin')==origin else None
        except (OSError,ValueError):return None

def remove_key(provider):
    with _lock:
        path=_path(provider)
        if path.exists():path.unlink()
        _memory.pop(provider,None)
