import {describe,expect,it} from 'vitest';
import {scanSummary,scopes,explain} from './language';

describe('Kullanıcıya gösterilen analizin sınırları',()=>{
  it.each(['failed','cancelled','running','queued'])('boş %s kontrolünü temiz sonuç saymaz',status=>{
    expect(scanSummary({status,analysis_complete:false,findings:[]}).complete).toBe(false);
  });
  it('tamamlandı denilen ama eksik kalan analizi tamamlanmış göstermez',()=>{
    expect(scanSummary({status:'completed',analysis_complete:false,findings:[]}).complete).toBe(false);
  });
  it('sıfır bulguyu güvenlik garantisi saymaz',()=>{
    const result=scanSummary({status:'completed',analysis_complete:true,findings:[]});
    expect(result.complete).toBe(true);
    expect(result.description).toContain('güvenli olduğu anlamına gelmez');
  });
  it('gözlem eksikliğini boş erişim kaydıyla karıştırmaz',()=>{
    expect(scopes(null)).toBe('Ölçülmedi');
    expect(scopes([])).toBe('Kayıt bulunmuyor');
    expect(scopes([{dynamic:true}])).toBe('Hedef kesin çözülemedi');
  });
  it('bilinmeyen motor kuralına uydurma bir neden atamaz',()=>{
    expect(explain({rule_id:'NEW-RULE'}).why).toContain('özgün açıklamasını');
  });
  it('uzak katalog incelemesini kaynak kod veya davranış analizi saymaz',()=>{
    const result=scanSummary({status:'completed',analysis_complete:true,analysis_kind:'remote_contract',findings:[]});
    expect(result.title).toBe('Araç tanımlarında uyarı bulunmadı');
    expect(result.description).toContain('Kaynak kodu incelenmedi');
    expect(result.description).toContain('çalışma davranışı ölçülmedi');
  });
  it('uzak bulgunun gerçek tanımını ve kapsamını korur',()=>{
    expect(explain({source:'remote_contract',title:'Tanım uyarısı',description:'Yalnız araç tanımı incelendi.',remediation:'Tanımı doğrula.'})).toEqual({title:'Tanım uyarısı',why:'Yalnız araç tanımı incelendi.',fix:'Tanımı doğrula.'});
  });
});
