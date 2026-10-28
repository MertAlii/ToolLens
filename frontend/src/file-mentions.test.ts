import {describe,it,expect} from 'vitest';
import {activeMention,insertMention,mentionPaths,mentionToken,removeMention} from './file-mentions';

describe('Dosya referansları',()=>{
 it('birden fazla dosyayı çözer, e-postayı dosya saymaz',()=>{
  expect(mentionPaths('@src/server.py ile @{proje notu.md} ilişkisi? mert@example.com')).toEqual(['src/server.py','proje notu.md']);
 });
 it('boşluklu ve Türkçe konumları kayıpsız korur',()=>{
  const path='araçlar/proje notu.md';expect(mentionPaths(mentionToken(path))).toEqual([path]);
 });
 it('imleçteki sorguyu bulur',()=>{
  expect(activeMention('Lütfen @src/se',14)?.query).toBe('src/se');
  expect(activeMention('mert@example.com',16)).toBeNull();
 });
 it('seçilen dosyayı imleçteki parçanın yerine koyar',()=>{
  expect(insertMention('@ser',4,'src/server.py')).toEqual({text:'@src/server.py ',caret:15});
 });
 it('soru ortasındaki eski tokenin tamamını değiştirir',()=>{
  const text='@server.py ne yapar?';expect(insertMention(text,4,'app.py').text).toBe('@app.py  ne yapar?');
 });
 it('bir referansı kaldırırken benzer adlı dosyayı bozmaz',()=>{
  expect(removeMention('@a.py @a.pyx @a.py','a.py')).toBe(' @a.pyx ');
 });
 it('aynı dosyayı iki kere bağlam saymaz',()=>{
  expect(mentionPaths('@a.py @a.py')).toEqual(['a.py']);
 });
});
