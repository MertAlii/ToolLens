"""Cancellable real model tests with observable state and a bounded lifetime."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, RLock
from time import monotonic
from uuid import uuid4
from . import providers

jobs={}
lock=RLock()
pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='model-test')


def view(job):
    return {k:v for k,v in job.items() if k not in ('cancel','started_clock')} | {'elapsed_seconds':round(monotonic()-job['started_clock'],1) if job['status'] in ('queued','running') else job.get('duration_seconds',0)}


def start(provider,model,config):
    if provider not in providers.PROVIDER_NAMES:raise ValueError('Bilinmeyen AI bağlantısı.')
    if not model:raise ValueError('Listeden bir model seçin.')
    with lock:
        if any(j['status'] in ('queued','running') for j in jobs.values()):
            raise ValueError('Bir model testi devam ediyor. Önce tamamlanmasını bekleyin veya iptal edin.')
        for key in list(jobs):
            if monotonic()-jobs[key]['started_clock']>3600:del jobs[key]
        job={'id':str(uuid4()),'provider':provider,'model':model,'status':'queued','cancel':Event(),'started_clock':monotonic()}
        jobs[job['id']]=job
    def run():
        job['status']='running'
        try:
            result=providers.generate(provider,model,'test',{'message':'Yalnız bağlantının çalıştığını tek cümleyle söyle.'},config={**config,'timeout_seconds':40,'validation_retries':0},cancel_event=job['cancel'])
            job.update(status='cancelled' if job['cancel'].is_set() else 'completed',result=result)
        except Exception as exc:job.update(status='cancelled' if job['cancel'].is_set() else 'failed',error=str(exc)[:800])
        finally:job['duration_seconds']=round(monotonic()-job['started_clock'],1)
    pool.submit(run)
    return view(job)


def get(key):
    with lock:
        if key not in jobs:raise KeyError('Model testi bulunamadı. Yeniden başlatın.')
        return view(jobs[key])


def cancel(key):
    with lock:
        if key not in jobs:raise KeyError('Model testi bulunamadı.')
        jobs[key]['cancel'].set()
        jobs[key]['cancellation_requested']=True
        return view(jobs[key])


def close():
    for job in jobs.values():job['cancel'].set()
    pool.shutdown(wait=False,cancel_futures=True)
