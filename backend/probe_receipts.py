"""Short-lived local evidence of an onboarding connection test."""
from copy import deepcopy
from threading import RLock
from time import monotonic
from uuid import uuid4
_lock=RLock()
_receipts={}

def issue(url,auth_env,transport,result):
    if result.get('status')!='connected':return result
    key=str(uuid4())
    with _lock:
        for old,(created,_,_) in list(_receipts.items()):
            if monotonic()-created>300:del _receipts[old]
        while len(_receipts)>=64:del _receipts[next(iter(_receipts))]
        _receipts[key]=(monotonic(),(url.strip(),auth_env or None,transport),deepcopy(result))
    return {**result,'probe_id':key}

def verified(key,url,auth_env,transport):
    with _lock:entry=_receipts.get(key)
    if not entry or monotonic()-entry[0]>300:raise ValueError('Bağlantı testinin süresi doldu. Projeyi oluşturmadan önce yeniden deneyin.')
    if entry[1]!=(url.strip(),auth_env or None,transport):raise ValueError('Bağlantı bilgileri değişti. Yeni bilgilerle bağlantıyı tekrar deneyin.')
    return deepcopy(entry[2])
