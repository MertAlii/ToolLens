import {describe,expect,it} from 'vitest';
import {classifyDecision,decisionGroups,evidenceBasis,isDecision} from './decision';

describe('Dörtlü karar kutusu',()=>{
 it('yüksek etki ve açık runtime kanıtını öncelikli düzeltmeye ayırır',()=>{
   expect(classifyDecision({impact:'High',evidence:{proof:{verdict:'violation_observed'}}})).toBe('fix_now');
 });
 it('AI onayı veya dinamik kaynak etiketi tek başına yeterli dayanak değildir',()=>{
   expect(classifyDecision({impact:'Critical',source:'dynamic',status:'confirmed',review:{status:'confirmed'}})).toBe('verify_now');
 });
 it('daha düşük etki ve insan kararını planlı düzeltme olarak ayrı etiketler',()=>{
   const finding={impact:'Medium',annotation:{decision:'confirmed',note:'Kaynak satırında sınırlamanın eksik olduğunu inceledim.'}};
   expect(classifyDecision(finding)).toBe('plan_fix');expect(evidenceBasis(finding)).toBe('human');
 });
 it('sınırlı kanıtta daha düşük etki için izle ve veri topla önerir',()=>{
   expect(classifyDecision({impact:'Low',annotation:{decision:'false_positive'}})).toBe('observe');
 });
 it('etki bilgisi bilinmiyorsa severity alanından tahmin etmez',()=>{
   expect(classifyDecision({severity:'Critical'})).toBe('unclassified');
   expect(classifyDecision({impact:'Unknown'})).toBe('unclassified');
 });
 it('birleştirilmiş provenance içindeki açık kanıtı tanır; eksik kanıtı kabul etmez',()=>{
   expect(evidenceBasis({impact:'High',provenance:[{evidence:{proof:{verdict:'violation_observed'}}}]})).toBe('runtime');
   expect(evidenceBasis({evidence:{proof:{verdict:'no_violation_observed'}}})).toBe('limited');
 });
 it('kutulardaki kayıtlar giriş kümesini tam ve tekrarsız böler',()=>{
   const findings=[{impact:'High'},{impact:'Medium'},{impact:'Critical',annotation:{decision:'confirmed',note:'Kod incelendi.'}},{impact:'Low',annotation:{decision:'confirmed',note:'Kod incelendi.'}},{title:'Bilinmiyor'}];
   const groups=decisionGroups(findings);expect(Object.values(groups).flat()).toHaveLength(5);
   expect(Object.values(groups).map(x=>x.length)).toEqual([1,1,1,1,1]);
   expect(Object.values(decisionGroups([])).flat()).toEqual([]);
 });
 it('URL filtresinde yalnız bilinen kutuları kabul eder',()=>{expect(isDecision('verify_now')).toBe(true);expect(isDecision('safe')).toBe(false);expect(isDecision(null)).toBe(false);});
 it('gerekçesiz insan kararı yeterli dayanak sayılmaz',()=>{
   for(const note of [undefined,null,'','   ']){
     const finding={impact:'High',annotation:{decision:'confirmed',note}};
     expect(evidenceBasis(finding)).toBe('limited');expect(classifyDecision(finding)).toBe('verify_now');
   }
 });
});
