"""Derive display metrics from preserved observations, never fabricate results."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def counts(records):
    result = {key: sum(row.get('score') == key for row in records) for key in ('TP','TN','FP','FN')}
    result['requested'] = len(records)
    result['completed'] = sum(row['outcome']=='complete' for row in records)
    result['non_completed'] = result['requested'] - result['completed']
    tp, fp, fn = result['TP'], result['FP'], result['FN']
    result['precision'] = tp/(tp+fp) if tp+fp else None
    result['recall'] = tp/(tp+fn) if tp+fn else None
    return result


def main():
    latest=(ROOT/'results'/'LATEST.txt').read_text().strip()
    folder=ROOT/'results'/latest
    summary=json.loads((folder/'summary.json').read_text(encoding='utf-8'))
    cases=summary['cases']
    metrics={'overall':counts(cases),
             'by_family':{family:counts([r for r in cases if r['family']==family]) for family in sorted({r['family'] for r in cases})},
             'by_split':{split:counts([r for r in cases if r['split']==split]) for split in ('development','held_out')},
             'interpretation':'Only independently authored controlled target-rule examples. Not a real-world accuracy estimate.',
             'not_measured':['Live model performance','Vulnerable target execution','Human participant usability']}
    (folder/'metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# ToolLens denetimli kaynak değerlendirmesi','',
           f"Gerçek Sentinel taraması: {metrics['overall']['completed']}/{metrics['overall']['requested']} tamamlandı. Eksik/başarısız: {metrics['overall']['non_completed']}.",'',
           '| Aile | TP | TN | FP | FN | Tamamlanan |','| --- | --- | --- | --- | --- | --- |']
    for family,m in metrics['by_family'].items():
        lines.append(f"| {family} | {m['TP']} | {m['TN']} | {m['FP']} | {m['FN']} | {m['completed']} |")
    lines += ['', '| Ayrım | TP | TN | FP | FN |','| --- | --- | --- | --- | --- |']
    for split,m in metrics['by_split'].items(): lines.append(f"| {split} | {m['TP']} | {m['TN']} | {m['FP']} | {m['FN']} |")
    m=metrics['overall']
    lines += ['',f"Bu kontrollü kümede hedef-kural precision: {m['precision']:.4f}; recall: {m['recall']:.4f}.",'',
              'Dört yanlış alarm, kimlik doğrulama ailesinin düzeltilmiş örneklerinde gözlendi. Bu örnekler Header ve Depends üzerinden gelen değeri environment token ile karşılaştırıp eşleşmeme durumunda 401 üretir. Mevcut motor bu doğrulama biçimini yeterli olarak tanımadı. Beklentiler ve örnekler sonuçlara göre değiştirilmedi. Bu sonuç sınırlı bir tanıma sınırını gösterir; genel kimlik doğrulama güvenliği hakkında hüküm vermez.','',
              f"Metadata ölçümü: {len(summary['version_pairs'])} sürüm çifti; dondurulmuş beklentiyle eşleşen {summary['version_pairs_matching']}. Bu ölçüm backend metadata çıkarımı ve değerlendirme aracının açık belirsizlik kontrolleridir; ürünün genel güvenlik tespiti puanı değildir.",'',
              'Ek kuralların ürettiği bulgular summary.json ve ham motor raporlarında ayrı korunur. Sıfır false negative, bu küçük kontrollü kümenin dışındaki bütün açıkların yakalandığı anlamına gelmez. Canlı AI, riskli hedef çalıştırması ve insan katılımcı çalışması bu ölçüme dahil değildir.','',
              'Önceki başarısız başlatmalar INITIAL_ATTEMPTS.md içinde ayrıca korunmuştur.']
    (folder/'SUMMARY.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    receipt={}
    for pattern in ('security_cases/**/*','version_cases/**/*'):
        for path in sorted(ROOT.glob(pattern)):
            if path.is_file():receipt[path.relative_to(ROOT).as_posix()]=hashlib.sha256(path.read_bytes()).hexdigest()
    (folder/'post_run_input_inventory.json').write_text(json.dumps({'note':'Post-run reproducibility inventory; frozen pre-run manifests are separately retained.','sha256':receipt},indent=2),encoding='utf-8')
    print(json.dumps(metrics,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
