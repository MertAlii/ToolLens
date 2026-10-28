import Editor,{DiffEditor,loader} from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
import EditorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';
import JsonWorker from 'monaco-editor/esm/vs/language/json/json.worker?worker';
import TypeScriptWorker from 'monaco-editor/esm/vs/language/typescript/ts.worker?worker';
import CssWorker from 'monaco-editor/esm/vs/language/css/css.worker?worker';
import HtmlWorker from 'monaco-editor/esm/vs/language/html/html.worker?worker';
import {useEffect,useRef,useState} from 'react';
(self as any).MonacoEnvironment={getWorker:(_:string,label:string)=>label==='json'?new JsonWorker():['javascript','typescript'].includes(label)?new TypeScriptWorker():['css','scss','less'].includes(label)?new CssWorker():['html','handlebars','razor'].includes(label)?new HtmlWorker():new EditorWorker()};
loader.config({monaco});
monaco.languages.json.jsonDefaults.setDiagnosticsOptions({validate:false,enableSchemaRequest:false});
monaco.languages.typescript.typescriptDefaults.setDiagnosticsOptions({noSemanticValidation:true,noSyntaxValidation:true,noSuggestionDiagnostics:true});
monaco.languages.typescript.javascriptDefaults.setDiagnosticsOptions({noSemanticValidation:true,noSyntaxValidation:true,noSuggestionDiagnostics:true});
export function CodeView({value,language='python',height=320,path,line}:{value:string,language?:string,height?:number,path?:string,line?:number}){
 const editor=useRef<monaco.editor.IStandaloneCodeEditor|null>(null);const [theme,setTheme]=useState(document.documentElement.dataset.theme==='light'?'vs':'vs-dark');
 useEffect(()=>{const observer=new MutationObserver(()=>setTheme(document.documentElement.dataset.theme==='light'?'vs':'vs-dark'));observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-theme']});return()=>observer.disconnect();},[]);
 function reveal(){const current=editor.current;if(!current)return;const target=Math.max(1,Math.min(line??1,current.getModel()?.getLineCount()??1));current.revealLineInCenter(target);if(line)current.setPosition({lineNumber:target,column:1});}
 useEffect(()=>{const frame=requestAnimationFrame(reveal);return()=>cancelAnimationFrame(frame);},[line,path,value]);
 return <div className="code-view"><Editor height={height} language={language} theme={theme} path={path} value={value} onMount={instance=>{editor.current=instance;reveal();}} options={{readOnly:true,domReadOnly:true,minimap:{enabled:false},fontFamily:'JetBrains Mono',fontSize:13,lineNumbers:'on',scrollBeyondLastLine:false,wordWrap:'on',automaticLayout:true,contextmenu:false,accessibilitySupport:'on',padding:{top:12,bottom:12},renderLineHighlight:'line',ariaLabel:'Salt okunur dosya içeriği'}}/></div>;
}
export function DiffView({before,after}:{before:string,after:string}){return <div className="code-view"><DiffEditor height={360} original={before} modified={after} theme="vs-dark" options={{readOnly:true,renderSideBySide:true,minimap:{enabled:false},fontSize:13,automaticLayout:true,scrollBeyondLastLine:false,accessibilitySupport:'on'}}/></div>;}
