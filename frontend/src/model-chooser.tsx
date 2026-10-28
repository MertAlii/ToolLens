import {useEffect,useRef,useState} from 'react';
import {Link} from 'react-router-dom';
import {useMutation,useQuery,useQueryClient} from '@tanstack/react-query';
import {Check,ChevronDown,ExternalLink,LoaderCircle,Search,Sparkles,Square} from 'lucide-react';
import {useWorkspace} from './App';
import {api,items,patch,post} from './api';
import {ErrorBox,Modal,Notice} from './ui';
import {ProviderIcon} from './settings-page';
import {notify} from './notifications';

import {providerNames,isAPI,cliProviders} from './provider-catalog';
export {providerNames} from './provider-catalog';
export function ModelChooser({disabled=false,compact=false}:{disabled?:boolean;compact?:boolean}){
 const w=useWorkspace();const qc=useQueryClient();const [open,setOpen]=useState(false);const [provider,setProvider]=useState(w.provider||'codex');const [model,setModel]=useState('');const [search,setSearch]=useState('');const [job,setJob]=useState('');const handled=useRef('');
 const currentCfg=w.settings.providers?.[w.provider]??{};
 useEffect(()=>{if(open){setProvider(w.provider||'codex');setModel(currentCfg.model??'');setSearch('');setJob('');}},[open]);
 const models=useQuery({queryKey:['models',provider],queryFn:()=>api(`/providers/${provider}/models`),enabled:open,staleTime:60000});
 const cfg=w.settings.providers?.[provider]??{};const options=items(models.data);const verified=model&&cfg.verified_model===model;
 const test=useMutation({mutationFn:()=>post(`/providers/${provider}/test-jobs`,{model,config:{...cfg,model}}),onSuccess:j=>{setJob(j.id);handled.current='';}});
 const state=useQuery({queryKey:['provider-test',job],queryFn:()=>api(`/provider-tests/${job}`),enabled:!!job,refetchInterval:q=>['queued','running'].includes(q.state.data?.status??'queued')?700:false});
 const running=test.isPending||!!job&&['queued','running'].includes(state.data?.status??'queued');
 const save=useMutation({mutationFn:()=>patch('/settings',{default_provider:provider,providers:{...w.settings.providers,[provider]:{...cfg,model,verified_model:model}}}),onSuccess:settings=>{qc.setQueryData(['settings'],settings);w.setProvider(provider);qc.invalidateQueries({queryKey:['settings']});notify('AI bağlantısı seçildi',`${providerNames[provider]} · ${model}`);setOpen(false);}});
 useEffect(()=>{if(job&&state.data?.status==='completed'&&handled.current!==job){handled.current=job;save.mutate();}},[state.data?.status,job]);
 const cancel=useMutation({mutationFn:()=>post(`/provider-tests/${job}/cancel`),onSuccess:()=>qc.invalidateQueries({queryKey:['provider-test',job]})});
 function chooseProvider(id:string){setProvider(id);setModel(w.settings.providers?.[id]?.model??'');setSearch('');setJob('');test.reset();save.reset();}
 const selected=w.providers.find(p=>p.id===provider);
 return <><button className={`model-trigger ${compact?'compact':''}`} disabled={disabled} onClick={()=>setOpen(true)} aria-label="Sohbet modelini seç" title="AI bağlantısını ve modeli değiştir"><span className={`provider-logo ${w.provider}`}><ProviderIcon id={w.provider}/></span><span>{currentCfg.model||'AI modeli seç'}{!compact&&<small>{currentCfg.verified_model===currentCfg.model&&currentCfg.model?'Yanıt testi doğrulandı':'Bir model seçip bağlantıyı dene'}</small>}</span><ChevronDown size={14}/></button>
 <Modal open={open} onOpenChange={value=>{if(!running&&!save.isPending)setOpen(value);}} title="Hangi modelle çalışalım?" description="Algılanan bağlantılardan seç. Yeni model, kısa bir yanıt testinden sonra kullanılır." wide><div className="model-provider-tabs provider-grid-v5" role="group" aria-label="Model sağlayıcıları">{Object.entries(providerNames).map(([id,name])=>{const p=w.providers.find(p=>p.id===id);return <button key={id} disabled={running||save.isPending||!isAPI(id)&&!p?.installed} className={provider===id?'selected':''} aria-pressed={provider===id} onClick={()=>chooseProvider(id)}><span className={`provider-logo ${id}`}><ProviderIcon id={id}/></span>{name}<small>{isAPI(id)?'API bağlantısı':p?.installed?'Algılandı':'Kurulu değil'}</small></button>;})}</div>
 <label className="model-search"><Search size={17}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Model ara…" aria-label="Modellerde ara" disabled={running}/></label><div className="model-options scroll-edges" role="group" aria-label="Kullanılabilir modeller">{models.isFetching?<p className="small muted">Model listesi alınıyor…</p>:options.filter(m=>`${m.display_name??''} ${m.id??m.name}`.toLocaleLowerCase('tr').includes(search.toLocaleLowerCase('tr'))).map(m=>{const id=m.id??m.name;return <button disabled={running||save.isPending} className={model===id?'selected':''} key={id} aria-pressed={model===id} onClick={()=>{setModel(id);setJob('');test.reset();save.reset();}}><span className={`provider-logo ${provider}`}><ProviderIcon id={provider}/></span><span><strong>{m.display_name??id}</strong><small>{id}{cfg.verified_model===id?' · Yanıt testi doğrulandı':''}</small></span>{model===id?<Check size={17}/>:<span className="model-radio"/>}</button>;})}{!models.isFetching&&!options.length&&<p className="small muted">Model listesi bulunamadı. Kurulum ve servis adresini Ayarlar’dan kontrol edebilirsin.</p>}</div>
 <p className="model-data-note">{provider==='ollama'?'Model, yapılandırdığın Ollama servisinde çalışır.':'Seçilen dosya içeriği, inceleme sırasında bu sağlayıcının model servisine gönderilir.'} Kurulum algılaması, hesabının tüm modellere erişebildiği anlamına gelmez.</p>
 {running&&<div className="test-progress" role="status"><LoaderCircle className="spin" size={17}/><span>Gerçek model yanıtı bekleniyor · {state.data?.elapsed_seconds??0} sn</span>{job&&<button className="text-button" disabled={cancel.isPending||state.data?.cancellation_requested} onClick={()=>cancel.mutate()}><Square size={13}/>İptal et</button>}</div>}
 {state.data?.status==='failed'&&<ErrorBox error={state.data.error}/>} {state.data?.status==='cancelled'&&<Notice>Test iptal edildi. Başka model seçebilirsin.</Notice>}<ErrorBox error={models.error??test.error??save.error??cancel.error}/>
 <div className="model-dialog-footer"><Link className="text-button" to="/ayarlar" onClick={()=>!running&&setOpen(false)} aria-disabled={running} style={running?{pointerEvents:'none'}:undefined}>Bağlantı ayarları <ExternalLink size={13}/></Link><button className="button primary" disabled={!model||running||save.isPending||(!selected?.installed&&!isAPI(provider))} onClick={()=>verified?save.mutate():test.mutate()}>{running||save.isPending?<LoaderCircle className="spin" size={15}/>:<Sparkles size={15}/ >}{verified?'Bu modeli kullan':'Test et ve kullan'}</button></div></Modal></>;
}
