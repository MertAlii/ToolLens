export function mentionToken(path:string){return /[\s@{}]/.test(path)?`@{${path}}`:`@${path}`;}
export function mentionPaths(text:string){
 const paths:string[]=[];const pattern=/(?<![\w@])@(?:\{([^}\r\n]+)\}|([^\s@{}]+))/g;
 for(const match of text.matchAll(pattern)){const path=match[1]??match[2].replace(/[.,;!?`]+$/,'');if(path&&!paths.includes(path))paths.push(path);}
 return paths;
}
export function removeMention(text:string,path:string){return text.replace(/(?<![\w@])@(?:\{([^}\r\n]+)\}|([^\s@{}]+))/g,(full,braced,plain)=>(braced??plain.replace(/[.,;!?`]+$/,''))===path?'':full);}
export function activeMention(text:string,caret:number){
 const before=text.slice(0,caret);const match=/(?:^|\s)@(?:\{([^}\r\n]*)|([^\s@{}]*))$/.exec(before);
 if(!match)return null;
 const start=before.lastIndexOf('@');let end=caret;
 if(match[1]!==undefined){const close=text.indexOf('}',caret);if(close>=0&&!text.slice(caret,close).includes('\n'))end=close+1;}
 else{const tail=/^[^\s@{}]*/.exec(text.slice(caret))?.[0]??'';end+=tail.length;}
 return {start,end,query:match[1]??match[2]??''};
}
export function insertMention(text:string,caret:number,path:string){
 const match=activeMention(text,caret);const token=mentionToken(path)+' ';
 const start=match?.start??caret;const end=match?.end??caret;
 return {text:text.slice(0,start)+token+text.slice(end),caret:start+token.length};
}
export function languageFor(path:string){const ext=path.split('.').pop()?.toLowerCase()??'';return ({py:'python',pyi:'python',ts:'typescript',tsx:'typescript',js:'javascript',jsx:'javascript',mjs:'javascript',json:'json',md:'markdown',yaml:'yaml',yml:'yaml',toml:'ini',html:'html',css:'css',scss:'scss',sql:'sql',sh:'shell',ps1:'powershell',rs:'rust',go:'go',java:'java',c:'c',h:'c',cpp:'cpp',xml:'xml'} as Record<string,string>)[ext]??'plaintext';}
