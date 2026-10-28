import {useEffect,useState} from 'react';
import {AlertCircle,CheckCircle2,Info,X} from 'lucide-react';
type Toast={id:string;title:string;description?:string;kind:'success'|'error'|'info'};
export function notify(title:string,description?:string,kind:Toast['kind']='success'){
 window.dispatchEvent(new CustomEvent('toollens-notice',{detail:{id:crypto.randomUUID(),title,description,kind}}));
}
function Notification({notice,onClose}:{notice:Toast;onClose:()=>void}){
 const [paused,setPaused]=useState(false);
 useEffect(()=>{if(paused||notice.kind==='error')return;const timer=setTimeout(onClose,8000);return()=>clearTimeout(timer);},[paused,onClose,notice.kind]);
 const Icon=notice.kind==='error'?AlertCircle:notice.kind==='success'?CheckCircle2:Info;
 return <article className={`toast-notice ${notice.kind}`} onMouseEnter={()=>setPaused(true)} onMouseLeave={()=>setPaused(false)} onFocus={()=>setPaused(true)} onBlur={()=>setPaused(false)} role={notice.kind==='error'?'alert':'status'}><span className="toast-symbol"><Icon size={20}/></span><div><strong>{notice.title}</strong>{notice.description&&<p>{notice.description}</p>}</div><button className="icon-button" aria-label={`Bildirimi kapat: ${notice.title}`} onClick={onClose}><X size={15}/></button></article>;
}
export function Notifications(){
 const [notices,setNotices]=useState<Toast[]>([]);
 useEffect(()=>{const listener=(event:Event)=>setNotices(old=>[...old.slice(-3),(event as CustomEvent<Toast>).detail]);window.addEventListener('toollens-notice',listener);return()=>window.removeEventListener('toollens-notice',listener);},[]);
 return <aside className="toast-stack" aria-label="Bildirimler">{notices.map(n=><Notification key={n.id} notice={n} onClose={()=>setNotices(old=>old.filter(item=>item.id!==n.id))}/>)}</aside>;
}
