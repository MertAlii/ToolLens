import {ArrowUpRight,Info} from 'lucide-react';
import type {Data} from './api';
import {Card} from './ui';
import {classifyDecision,decisionGroups,decisionOptions,decisionTitle,evidenceBasis,evidenceLabel} from './decision';
import type {DecisionId} from './decision';

export function DecisionMatrix({findings,onSelect,selected,scope='Bu kontrolün bulguları'}:{findings:Data[];onSelect:(id:DecisionId)=>void;selected?:DecisionId|null;scope?:string}) {
 const groups=decisionGroups(findings);
 return <Card className="decision-card section-gap" title="Dörtlü karar kutusu" description={`${scope} · Olası etki × kanıt yeterliliği`}>
  <p className="decision-intro">Aracı geliştiren kişiyle kullanan kişi aynı bilgiye sahip olmayabilir. Bu <strong>bilgi asimetrisini</strong> azaltmak için beyanı, kodu ve test kanıtını birlikte görün. Kutular bir sonraki inceleme adımını önerir; otomatik karar vermez.</p>
  <div className="decision-grid" role="group" aria-label="Olası etki ve kanıt yeterliliğine göre inceleme önerileri">
   {decisionOptions.map(option=><button className={`decision-box ${option.id} ${selected===option.id?'is-selected':''}`} type="button" key={option.id} aria-pressed={selected===option.id} onClick={()=>onSelect(option.id)}>
     <span className="decision-coordinate"><span>{option.impact}</span><span>{option.evidence}</span></span>
     <span className="decision-box-heading"><strong>{option.title}</strong><span className="decision-count">{groups[option.id].length}</span></span>
     <span className="decision-action">{option.action}</span>
     <span className="decision-link">Bulguları incele <ArrowUpRight size={14}/></span>
   </button>)}
  </div>
  {groups.unclassified.length>0&&<button type="button" className="text-button decision-unclassified" aria-pressed={selected==='unclassified'} onClick={()=>onSelect('unclassified')}>{groups.unclassified.length} bulgu sınıflandırılmadı: etki bilgisi eksik veya tanınmıyor.</button>}
  {!findings.length&&<p className="decision-empty">Bu kapsamda sınıflandırılacak bulgu yok. Dört kutunun boş olması güvenlik garantisi değildir.</p>}
  <details className="decision-method"><summary><Info size={14}/> Sınıflandırma nasıl yapılıyor?</summary><p>Olası etki, motorun etki alanından alınır. Kritik/yüksek etki ayrı gruptadır. Yeterli dayanak için açık runtime ihlal kanıtı veya kullanıcının gerekçe notu içeren “Gerçek sorun” değerlendirmesi gerekir. İnsan değerlendirmesi runtime kanıtı değildir. Statik tespit ve AI onayı tek başına yeterli dayanak sayılmaz. Etki bilgisi eksik bulgular kutulara zorlanmaz.</p></details>
 </Card>;
}

export function DecisionSummary({finding}:{finding:Data}) {
 const id=classifyDecision(finding);const basis=evidenceBasis(finding);
 return <section className={`decision-summary ${id}`} aria-label="İnceleme önerisi"><div><small>SONRAKİ İNCELEME ADIMI</small><strong>{decisionTitle(id)}</strong></div><p>{evidenceLabel(basis)}{id==='unclassified'?'. Etki bilgisi olmadan dört kutudan biri seçilmedi.':'. Bu öneri kullanıcı kararının yerine geçmez.'}</p></section>;
}
