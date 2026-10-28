import {useEffect,useRef,useState} from 'react';
import {Check,ChevronDown,Monitor,Moon,Sun} from 'lucide-react';
type Preference='system'|'dark'|'light';
export function ThemeMenu(){
 const initial=localStorage.getItem('toollens-theme');const [choice,setChoice]=useState<Preference>(initial==='light'||initial==='system'?initial:'dark');const [systemDark,setSystemDark]=useState(window.matchMedia('(prefers-color-scheme: dark)').matches);const [open,setOpen]=useState(false);const container=useRef<HTMLDivElement>(null);const trigger=useRef<HTMLButtonElement>(null);
 useEffect(()=>{const query=window.matchMedia('(prefers-color-scheme: dark)');const update=()=>setSystemDark(query.matches);query.addEventListener('change',update);return()=>query.removeEventListener('change',update);},[]);
 useEffect(()=>{document.documentElement.dataset.theme=choice==='system'?(systemDark?'dark':'light'):choice;localStorage.setItem('toollens-theme',choice);},[choice,systemDark]);
 useEffect(()=>{if(!open)return;const outside=(event:PointerEvent)=>{if(!container.current?.contains(event.target as Node))setOpen(false);};const escape=(event:KeyboardEvent)=>{if(event.key==='Escape'){setOpen(false);trigger.current?.focus();}};document.addEventListener('pointerdown',outside);document.addEventListener('keydown',escape);return()=>{document.removeEventListener('pointerdown',outside);document.removeEventListener('keydown',escape);};},[open]);
 const Icon=choice==='system'?Monitor:choice==='dark'?Moon:Sun;
 const options=[{id:'system' as const,name:'Sistem',icon:Monitor},{id:'dark' as const,name:'Dark',icon:Moon},{id:'light' as const,name:'Beyaz',icon:Sun}];
 return <div className="theme-menu" ref={container}><button ref={trigger} className="theme-trigger" aria-label="Tema seç" aria-expanded={open} aria-controls="theme-options" onClick={()=>setOpen(!open)}><Icon size={17}/><ChevronDown size={12}/></button>{open&&<div id="theme-options" className="theme-options" aria-label="Tema seçenekleri">{options.map(option=><button key={option.id} aria-pressed={choice===option.id} onClick={()=>{setChoice(option.id);setOpen(false);trigger.current?.focus();}}><option.icon size={16}/><span>{option.name}</span>{choice===option.id&&<Check size={14}/>}</button>)}</div>}</div>;
}
