import {createContext,useContext,useEffect,useRef,useState} from 'react';
import type {ReactNode} from 'react';
import {Link,NavLink,Navigate,Route,Routes,useNavigate,useLocation} from 'react-router-dom';
import {useQuery} from '@tanstack/react-query';
import {ArrowRight,ArrowUpRight,BookOpen,Check,ChevronRight,CircleHelp,Code2,FileCheck2,Folder,FolderOpen,House,Layers3,LockKeyhole,Monitor,Moon,ScanLine,ShieldCheck,Settings,SlidersHorizontal,Sun,Unplug,Workflow} from 'lucide-react';
import {api,items} from './api';
import type {Data} from './api';
import {Modal} from './ui';
import {WorkspacePage} from './studio';
import {SettingsPage} from './settings-page';
import {LandingPage,ProjectsPage,CreateProjectPage,ProjectWorkspace} from './product-pages';
import {Notifications} from './notifications';
import {ThemeMenu} from './theme-menu';
interface Workspace{technical:boolean;setTechnical:(v:boolean)=>void;newScan:(project?:string)=>void;projectId:string;setProjectId:(v:string)=>void;provider:string;setProvider:(v:string)=>void;projects:Data[];scans:Data[];providers:Data[];health:Data;settings:Data;openConnections:()=>void;}
const Context=createContext<Workspace>(null!);export const useWorkspace=()=>useContext(Context);
export default function App(){
 const location=useLocation();const nav=useNavigate();const [projectId,setProjectId]=useState('');const [technical,setTechnical]=useState(false);const [help,setHelp]=useState(false);const [provider,setProvider]=useState(localStorage.getItem('toollens-provider')??'');

 const health=useQuery({queryKey:['health'],queryFn:()=>api('/health'),refetchInterval:30000});const projects=useQuery({queryKey:['projects'],queryFn:()=>api('/projects')});const scans=useQuery({queryKey:['scans'],queryFn:()=>api('/scans'),refetchInterval:4000});const settings=useQuery({queryKey:['settings'],queryFn:()=>api('/settings')});const providers=useQuery({queryKey:['providers'],queryFn:()=>api('/providers'),staleTime:60000});
 const value:Workspace={technical,setTechnical,projectId,setProjectId,provider:provider||settings.data?.default_provider||'',setProvider:(v)=>{setProvider(v);localStorage.setItem('toollens-provider',v);},projects:items(projects.data),scans:items(scans.data),providers:items(providers.data),health:health.data??{},settings:settings.data??{},openConnections:()=>nav('/ayarlar'),newScan:(id)=>{if(id)setProjectId(id);nav(id?`/calisma?proje=${id}`:'/yeni-proje');}};
 return <Context.Provider value={value}><a className="skip-link" href="#main">İçeriğe geç</a><header className={`site-header ${location.pathname==='/'?'landing-header':''}`}><div className="header-inner"><Link to="/" className="brand" aria-label="ToolLens ana sayfa"><img src="/toollens-logo.png" alt=""/><span>ToolLens<span className="brand-period">.</span></span></Link><div className="header-actions"><ThemeMenu/><button className="icon-button compact-settings" title="Ayarlar" aria-label="Ayarlar" onClick={()=>nav('/ayarlar')}><Settings size={19}/></button></div></div></header><main id="main" tabIndex={-1}><Routes><Route path="/" element={<LandingPage/>}/><Route path="/projeler" element={<ProjectsPage/>}/><Route path="/yeni-proje" element={<CreateProjectPage/>}/><Route path="/calisma" element={<ProjectWorkspace/>}/><Route path="/ayarlar" element={<SettingsPage/>}/><Route path="*" element={<Navigate to="/calisma" replace/>}/></Routes></main><footer className="site-footer"><Link className="footer-brand" to="/">ToolLens.</Link><span>Yapay zekâ araçlarını anlamak için.</span><span className="service-status"><i/>{health.isError?'Yerel servisle bağlantı kurulamadı':health.isSuccess?'Bu bilgisayarda çalışıyor':'Yerel servis bekleniyor'}</span></footer><Notifications/></Context.Provider>;
}
export function Intro({eyebrow,title,children,action}:{eyebrow?:string;title:string;children?:ReactNode;action?:ReactNode}){return <div className="intro"><div>{eyebrow&&<span className="eyebrow">{eyebrow}</span>}<h1>{title}</h1>{children&&<p>{children}</p>}</div>{action}</div>;}
