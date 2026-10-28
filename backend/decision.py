"""Transparent action guidance, not a probability or automatic security verdict."""
from __future__ import annotations

POLICY_VERSION = "tl-decision-v1"
BOXES = {
    "fix_now": {"label": "Öncelikli düzelt", "action": "Yüksek etkili bulguyu kanıtıyla birlikte önceliklendir ve düzeltmeyi doğrula."},
    "verify_now": {"label": "Öncelikli doğrula", "action": "Olası etki yüksek; kesin karar öncesinde eksik kanıtı tamamla."},
    "plan_fix": {"label": "Planlı düzelt", "action": "Kanıtlanan konuyu kapsamına uygun iş planına al ve yeniden kontrol et."},
    "observe": {"label": "İzle ve veri topla", "action": "Sınırlı kanıtı koru; bu görünüm güvenli olduğu veya işlem gerekmediği anlamına gelmez."},
    "unclassified": {"label": "Sınıflandırılmadı", "action": "Etki bilgisi eksik; sınıflandırma için teknik inceleme gerekli."},
}


def classify_decision(finding):
    impact = finding.get('impact')
    if impact in ('Critical', 'High'):
        effect = 'high'
    elif impact in ('Medium', 'Low', 'Informational'):
        effect = 'lower'
    else:
        effect = 'unknown'
    sources = []
    candidates = [finding.get('evidence')]
    candidates.extend(item.get('evidence') for item in finding.get('provenance', []) if isinstance(item, dict))
    if any(isinstance(evidence, dict) and isinstance(evidence.get('proof'), dict)
           and evidence['proof'].get('verdict') == 'violation_observed' for evidence in candidates):
        sources.append('runtime_proof')
    annotation = finding.get('annotation') or {}
    if annotation.get('decision') == 'confirmed' and isinstance(annotation.get('note'), str) and annotation['note'].strip():
        sources.append('human_assessment')
    sufficient = bool(sources)
    box = ('fix_now' if sufficient else 'verify_now') if effect == 'high' else (
        ('plan_fix' if sufficient else 'observe') if effect == 'lower' else 'unclassified')
    return {'policy_version': POLICY_VERSION, 'box': box, **BOXES[box],
            'impact_band': effect, 'evidence_level': 'sufficient' if sufficient else 'limited',
            'evidence_sources': sources,
            'limitation': 'İnsan değerlendirmesi runtime kanıtı değildir. Statik eşleşme veya AI onayı tek başına yeterli kanıt sayılmaz.'}


def summarize_decisions(findings):
    counts = {key: 0 for key in BOXES}
    for finding in findings:
        counts[classify_decision(finding)['box']] += 1
    return {'policy_version': POLICY_VERSION, 'total': len(findings), 'counts': counts,
            'boxes': [{'id': key, **value, 'count': counts[key]} for key, value in BOXES.items()],
            'scope': 'Bu kontroldeki bulgular; otomatik güvenlik onayı veya mali zarar tahmini değildir.'}
