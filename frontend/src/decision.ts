import type {Data} from './api';

export type DecisionId = 'fix_now'|'verify_now'|'plan_fix'|'observe'|'unclassified';
export type EvidenceBasis = 'runtime'|'human'|'limited';
export const decisionOptions: {id:Exclude<DecisionId,'unclassified'>;title:string;impact:string;evidence:string;action:string}[] = [
  {id:'fix_now',title:'Öncelikli düzelt',impact:'Yüksek olası etki',evidence:'Yeterli dayanak',action:'Kanıtı koruyun; düzeltmeyi önceliklendirin ve yeniden kontrol edin.'},
  {id:'verify_now',title:'Öncelikli doğrula',impact:'Yüksek olası etki',evidence:'Sınırlı dayanak',action:'Belirsizliği önce azaltın; ilgili kodu veya desteklenen testi inceleyin.'},
  {id:'plan_fix',title:'Planlı düzelt',impact:'Daha düşük olası etki',evidence:'Yeterli dayanak',action:'Düzeltmeyi iş planına alın; sonrasında aynı kapsamla kontrol edin.'},
  {id:'observe',title:'İzle ve veri topla',impact:'Daha düşük olası etki',evidence:'Sınırlı dayanak',action:'Eksik bilgiyi kaydedin ve incelemeyi sürdürün. Bu kutu güvenli onayı değildir.'},
];

export function evidenceBasis(finding:Data):EvidenceBasis {
  // A dynamic origin, an AI confirmation or the existence of logs alone is not proof.
  const evidence=[finding.evidence,...(Array.isArray(finding.provenance)?finding.provenance.map((p:Data)=>p?.evidence):[])];
  if(evidence.some(e=>e?.proof?.verdict==='violation_observed'))return 'runtime';
  if(finding.annotation?.decision==='confirmed'&&typeof finding.annotation?.note==='string'&&finding.annotation.note.trim().length>0)return 'human';
  return 'limited';
}

export function classifyDecision(finding:Data):DecisionId {
  const impact=finding.impact;
  if(!['Critical','High','Medium','Low','Informational'].includes(impact))return 'unclassified';
  const high=impact==='Critical'||impact==='High';
  const sufficient=evidenceBasis(finding)!=='limited';
  return high?(sufficient?'fix_now':'verify_now'):(sufficient?'plan_fix':'observe');
}

export const decisionTitle=(id:DecisionId)=>decisionOptions.find(x=>x.id===id)?.title??'Sınıflandırılmadı';
export const evidenceLabel=(basis:EvidenceBasis)=>basis==='runtime'?'İzole testte kaydedilmiş ihlal kanıtı':basis==='human'?'Kullanıcının gerekçeli gerçek sorun değerlendirmesi':'Statik tespit veya AI yorumu; ek doğrulama gerekli';
export const isDecision=(value:string|null):value is DecisionId=>[...decisionOptions.map(x=>x.id),'unclassified'].includes(value??'');

export function decisionGroups(findings:Data[]):Record<DecisionId,Data[]> {
  const groups:Record<DecisionId,Data[]>={fix_now:[],verify_now:[],plan_fix:[],observe:[],unclassified:[]};
  for(const finding of findings)groups[classifyDecision(finding)].push(finding);
  return groups;
}
