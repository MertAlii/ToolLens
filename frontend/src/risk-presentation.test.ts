import {describe,it,expect} from 'vitest';
import {riskDisplay} from './risk-presentation';
describe('scoped risk presentation',()=>{
 it('does not display remote zero as a safety score',()=>{const x=riskDisplay({scope:'contract_only',value:0,status:'calculated',label:'legacy label'});expect(x.showNumber).toBe(false);expect(x.value).toBe(null);expect(x.title).toContain('Araç tanımlarında');expect(x.note).toContain('davranışı ölçülmedi');});
 it('keeps positive contract priority scoped to descriptions',()=>{const x=riskDisplay({scope:'contract_only',value:35,status:'calculated',label:'Orta öncelik'});expect(x.value).toBe(35);expect(x.heading).toBe('ARAÇ TANIMI ÖNCELİĞİ');});
 it('keeps a completed source score visible without a percentage claim',()=>{const x=riskDisplay({scope:'source_only',value:0,status:'calculated',label:'İncelenen kapsamda 0'});expect(x.showNumber).toBe(true);expect(x.note).toContain('olasılık yüzdesi');});
 it('does not show a numeric incomplete result',()=>{expect(riskDisplay({scope:'source_and_runtime',value:null,status:'unknown'}).showNumber).toBe(false);});
});
