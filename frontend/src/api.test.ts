import {describe,expect,it} from 'vitest';
import {items,isActive,label,plain} from './api';
describe('Backend verisinin sunumu',()=>{
 it('liste sarmalayıcısını ve model adlarını normalize eder',()=>{expect(items({items:[{id:'a'}]})).toEqual([{id:'a'}]);expect(items(['model-x'])).toEqual([{id:'model-x',name:'model-x'}]);expect(items(undefined)).toEqual([]);});
 it('ölçülmeyen alanı erişim yok gibi sunmaz',()=>{expect(label('not_measured')).toBe('Ölçülmedi');expect(plain(null)).toBe('Bilinmiyor');expect(label('declaration_missing')).toBe('Beyan bulunamadı');});
 it('eksik ve başarısız taramayı çalışan veya tamamlanmış saymaz',()=>{expect(isActive({status:'incomplete'})).toBe(false);expect(isActive({status:'failed'})).toBe(false);expect(isActive({status:'running'})).toBe(true);expect(label('incomplete')).toBe('Eksik analiz');});
});
