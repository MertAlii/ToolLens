export type Data = Record<string, any>;
export const items = (value: any): Data[] => (Array.isArray(value) ? value : value?.items ?? []).map((v:any)=>typeof v==='string'?{id:v,name:v}:v);
export async function api<T = any>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try { response = await fetch(`/api${path}`, { signal: AbortSignal.timeout(init?.method && init.method!=='GET' ? 190000 : 25000), ...init, headers: { 'Content-Type': 'application/json', ...init?.headers } }); }
  catch { throw new Error('Yerel servis yanıt vermedi. ToolLens sunucusunun çalıştığını kontrol edin.'); }
  if (!response.ok) {
    let message = `İşlem tamamlanamadı (${response.status}).`;
    try { const body = await response.json(); message = typeof body.detail === 'string' ? body.detail : body.error ?? body.message ?? JSON.stringify(body.detail ?? body); } catch { /* non-JSON */ }
    throw new Error(message);
  }
  return response.status === 204 ? undefined as T : response.json();
}
export const post = <T = any>(path: string, body: any = {}) => api<T>(path, { method: 'POST', body: JSON.stringify(body) });
export const patch = <T = any>(path: string, body: any = {}) => api<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
export const idOf = (value: Data) => String(value.id ?? value.finding_id ?? value.name ?? '');
export const stateLabels: Record<string, string> = {queued:'Sırada',running:'Çalışıyor',completed:'Tamamlandı',incomplete:'Eksik analiz',failed:'Başarısız',cancelled:'İptal edildi',pending:'Bekliyor',succeeded:'Tamamlandı',skipped:'Çalıştırılmadı',needs_review:'İnceleme gerekli',confirmed:'Doğrulandı',likely_false_positive:'Olası yanlış alarm',suppressed:'Bastırıldı',unknown:'Bilinmiyor',not_measured:'Ölçülmedi',undeclared:'Beyan bulunamadı',potential_mismatch:'Kodda uyumsuzluk şüphesi',inconclusive:'Sonuçlandırılamadı',observed_violation:'Testte ihlal gözlendi',no_mismatch:'İncelenen kapsamda uyumsuzluk bulunmadı',sandbox_blocked:'Test ortamı tarafından engellendi'};
Object.assign(stateLabels,{cancelling:'Durduruluyor',runtime_violation:'Testte ihlal gözlendi',violation_observed:'İhlal gözlendi',declaration_missing:'Beyan bulunamadı',unresolved:'Çözümlenemedi',static_mismatch:'Kodda kapsam uyuşmazlığı şüphesi',no_static_mismatch_observed:'İncelenen kapsamda uyumsuzluk bulunmadı',available:'Kullanılabilir',installed:'Kurulu',not_installed:'Kurulu değil',stopped:'Durduruldu',starting:'Başlatılıyor',blocked:'Ortam hazır değil',not_checked:'Kontrol edilmedi',authenticated:'Oturum açık',unauthenticated:'Oturum gerekli',local:'Yerel',cloud:'Sağlayıcı servisi'});
export const label = (value: any) => stateLabels[value] ?? value ?? 'Bilinmiyor';
export const severityLabels: Record<string,string> = {Critical:'Kritik',High:'Yüksek',Medium:'Orta',Low:'Düşük',Informational:'Bilgi'};
export const severityLabel = (value: any) => severityLabels[value] ?? value ?? 'Belirtilmedi';
export const date = (value: any) => value ? new Intl.DateTimeFormat('tr-TR',{dateStyle:'medium',timeStyle:'short'}).format(new Date(value)) : 'Henüz yok';
export function plain(value: any): string { if (value === null || value === undefined) return 'Bilinmiyor'; if(typeof value === 'string') return value; if(Array.isArray(value)) return value.length ? value.map(plain).join(', ') : 'Kayıt yok'; return JSON.stringify(value,null,2); }
export function download(name:string, content:string, type='text/plain') {const url=URL.createObjectURL(new Blob([content],{type}));const a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
export const isActive = (scan: Data) => ['queued','running','cancelling'].includes(scan.status);
export function comparisonCount(result:Data):number {return Array.isArray(result.new_findings)?result.new_findings.length:Array.isArray(result.findings?.new)?result.findings.new.length:0;}
