import type {Data} from './api';
export function riskDisplay(score:Data){
 const contract=score.scope==='contract_only';
 const showNumber=score.value!==null&&score.status==='calculated'&&!(contract&&score.value===0);
 return {contract,showNumber,value:showNumber?score.value:null,heading:contract?'ARAÇ TANIMI ÖNCELİĞİ':'RİSK ÖNCELİK PUANI',title:contract&&score.value===0?'Araç tanımlarında uyarı bulunmadı':score.label,scope:contract?'Yalnız sunucunun yayımladığı tanımlar':score.scope==='source_and_runtime'?'Kaynak kodu ve izole test':'Kaynak kod incelemesi',note:contract?'Kaynak kodu incelenmedi; çalışma davranışı ölçülmedi. Bu değerlendirme yalnız alınan araç tanımları içindir.':'Bulgu önemlerine göre hesaplanır. Bir olasılık yüzdesi veya güvenlik onayı değildir.'};
}
export const basisLabel=(value:string)=>({runtime_proven:'Testte doğrulanmış ihlal',static:'Kaynak kod incelemesi',contract:'Sunucunun araç tanımı',unverified_dynamic:'Doğrulanmamış test kaydı',unknown:'Dayanak belirtilmedi'}[value]??'Dayanak belirtilmedi');
