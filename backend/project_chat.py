"""Durable, cancellable file questions with immutable source copies."""
from concurrent.futures import ThreadPoolExecutor
import json
import threading
from time import monotonic
from . import providers
from .storage import now
from .project_files import prepare_question


class ProjectChat:
    def __init__(self,store):
        self.store=store;self.pool=ThreadPoolExecutor(max_workers=2,thread_name_prefix='file-question')
        self.lock=threading.RLock();self.events={};self.started={}
        for message in self.store.all('file_chat'):
            if message['status'] in ('queued','running'):
                message.update(status='failed',error='Uygulama yanıt tamamlanmadan kapandı. Soruyu yeniden gönderebilirsiniz.',completed_at=now())
                self.store.put('file_chat',message)

    def public(self,message):
        data={k:v for k,v in message.items() if k!='source_copies'}
        started=self.started.get(data['id'])
        if started is not None:data['elapsed_seconds']=round(monotonic()-started,1)
        return data

    def history(self,project_id):
        return [self.public(m) for m in self.store.all('file_chat') if m['project_id']==project_id][::-1]

    def get(self,project_id,key):
        message=self.store.get('file_chat',key)
        if not message or message['project_id']!=project_id:raise KeyError('Dosya sorusu bulunamadı.')
        return message

    def start(self,project,root,question,paths,provider,model,config):
        question=question.strip()
        if not question:raise ValueError('Dosyalar hakkında sorunuzu yazın.')
        if len(question)>4000:raise ValueError('Soru en fazla 4000 karakter olabilir.')
        files,context=prepare_question(root,question,paths,allow_empty=True)
        context['project_name']=project.get('name','Proje')
        if not files:context['scope']='Genel sohbet. Hiçbir proje dosyası okunmadı veya gönderilmedi. Dosya içeriği hakkında çıkarım yapma; kullanıcı isterse @ ile dosya ekleyebilir.'
        hashes={f['path']:f['hash'] for f in files};previous=[]
        for old in self.store.all('file_chat'):
            if old.get('project_id')!=project['id'] or old.get('status')!='completed' or old.get('provider')!=provider or old.get('model')!=model:continue
            if {f['path']:f['hash'] for f in old.get('files',[])}!=hashes:continue
            item={'question':old['question'],'answer':old['content']}
            if len(json.dumps({**context,'previous_messages':[item,*previous]},ensure_ascii=False).encode())<providers.MAX_CONTEXT_BYTES-1500:
                previous.insert(0,item)
            if len(previous)==2:break
        if previous:context['previous_messages']=previous
        # Send bounded, sanitized evidence. Keep original copies in the local
        # store for reference review, never in a background tool's working folder.
        context=providers._sanitize_context(context)
        with self.lock:
            if any(m['status'] in ('queued','running') for m in self.store.all('file_chat')):
                raise ValueError('Bir dosya sorusu yanıtlanıyor. Önce tamamlanmasını bekleyin veya iptal edin.')
            message=self.store.new('file_chat',project_id=project['id'],question=question,provider=provider,model=model,status='queued',files=[{k:v for k,v in f.items() if k!='content'} for f in files],source_copies=files,content=None,evidence_refs=[],created_at=now())
            key=message['id'];event=threading.Event();self.events[key]=event;self.started[key]=monotonic()
        def update(**changes):
            with self.lock:
                current=self.store.get('file_chat',key);current.update(changes);self.store.put('file_chat',current)
        def run():
            try:
                if event.is_set():raise InterruptedError('Soru iptal edildi.')
                update(status='running')
                answer=providers.generate(provider,model,'chat',context,detail='simple',cancel_event=event,config={**config,'timeout_seconds':90})
                with self.lock:
                    if event.is_set():raise InterruptedError('Soru iptal edildi.')
                    update(**{**answer,'status':'completed','completed_at':now()})
            except Exception as exc:update(status='cancelled' if event.is_set() else 'failed',error=str(exc)[:1200],completed_at=now())
            finally:
                update(duration_seconds=round(monotonic()-self.started[key],1));self.events.pop(key,None);self.started.pop(key,None)
        self.pool.submit(run)
        return self.public(message)

    def cancel(self,project_id,key):
        with self.lock:
            message=self.get(project_id,key)
            event=self.events.get(key)
            if event is not None and message['status'] in ('queued','running'):
                event.set();message['cancellation_requested']=True;self.store.put('file_chat',message)
            return self.public(message)

    def close(self):
        for event in list(self.events.values()):event.set()
        self.pool.shutdown(wait=False,cancel_futures=True)
