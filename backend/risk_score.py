"""Auditable prioritization index. Never a probability or safety certificate.

The strongest finding determines the band. Additional non-informational
findings add at most ten points, so many low findings cannot replace a
critical one. Evidence certainty is reported separately and never inflated
by an AI review or an annotation.
"""
from __future__ import annotations

import hashlib
import json

POLICY_VERSION = 'toollens-risk-v1'
WEIGHTS = {'Critical': 90, 'High': 65, 'Medium': 35, 'Low': 10, 'Informational': 0}
FORMULA = 'min(100, en yüksek önem ağırlığı + min(10, 2 × max(0, puan ekleyen benzersiz bulgu sayısı − 1)))'


def _identity(finding, index):
    key = finding.get('finding_id')
    if isinstance(key, str) and key.strip():
        return key
    # An absent ID is not grounds to count the same record repeatedly.
    identity = {name: finding.get(name) for name in ('rule_id', 'source', 'location', 'title')}
    if not any(identity.get(name) for name in ('rule_id', 'location', 'title')):
        return f'unidentified-{index}'
    return 'derived-' + hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:20]


def _basis(rows):
    evidence = []
    for row in rows:
        evidence.append(row.get('evidence'))
        evidence.extend(p.get('evidence') for p in row.get('provenance', []) if isinstance(p, dict))
    if any(isinstance(e, dict) and isinstance(e.get('proof'), dict)
           and e['proof'].get('verdict') == 'violation_observed' for e in evidence):
        return 'runtime_proven'
    sources = {row.get('source') for row in rows}
    if 'dynamic' in sources:
        return 'unverified_dynamic'
    if 'remote_contract' in sources:
        return 'contract'
    if 'static' in sources:
        return 'static'
    return 'unknown'


def calculate_risk(scan):
    """Return deterministic, JSON-safe metadata without mutating scan/findings.

    Incomplete input, unsupported severities and incomplete runtime tests
    cannot yield zero. Duplicate IDs retain the highest reported severity;
    a conflicting or absent severity keeps the whole result unscored.
    """
    rows = scan.get('findings')
    rows_available = isinstance(rows, list) and all(isinstance(f, dict) for f in rows)
    rows = rows if rows_available else []
    contract = scan.get('analysis_kind') == 'remote_contract' or any(f.get('source') == 'remote_contract' for f in rows)
    scope = 'contract_only' if contract else 'source_and_runtime' if scan.get('profile') == 'dynamic' else 'source_only'
    groups = {}
    for index, finding in enumerate(rows):
        groups.setdefault(_identity(finding, index), []).append(finding)
    factors = []
    counts = {severity: 0 for severity in WEIGHTS}
    counts['Unknown'] = 0
    evidence_counts = {key: 0 for key in ('runtime_proven', 'static', 'contract', 'unverified_dynamic', 'unknown')}
    for key, duplicates in sorted(groups.items()):
        severities = [f.get('severity') for f in duplicates]
        severity = max(severities, key=WEIGHTS.get) if all(s in WEIGHTS for s in severities) else 'Unknown'
        basis = _basis(duplicates)
        counts[severity] += 1
        evidence_counts[basis] += 1
        rule_ids = sorted({f['rule_id'] for f in duplicates if isinstance(f.get('rule_id'), str)})
        refs=[]
        for row in duplicates:
            loc=row.get('location') or {};path=loc.get('path');region=loc.get('range') or {}
            if not path:continue
            ref={'path':path,'kind':loc.get('kind','source')}
            if isinstance(region.get('start_line'),int) and region['start_line']>0:
                ref['start_line']=region['start_line'];ref['end_line']=region.get('end_line',region['start_line'])
            if ref not in refs:refs.append(ref)
        refs=sorted(refs,key=lambda ref:json.dumps(ref,sort_keys=True))
        factors.append({'source_refs':refs,'finding_id': key, 'rule_id': rule_ids[0] if rule_ids else None,
                        'severity': severity, 'weight': WEIGHTS.get(severity), 'evidence_basis': basis})
    limitations = [
        'Bu değer güvenlik olasılığı, saldırı ihtimali veya güvenlik sertifikası değildir; inceleme önceliğini gösterir.',
        'Sıfır puan yalnız tamamlanan kapsamda puan ekleyen bulgu bulunmadığı anlamına gelir.',
        'AI yorumu ve kullanıcı notu önem ağırlığını değiştirmez; yanlış alarm işareti özgün bulguyu puandan düşürmez.',
        'Statik veya araç tanımı tespiti, çalışma sırasında doğrulanmış ihlal değildir. Kanıt türleri ayrıca gösterilir.',
    ]
    if contract:
        limitations.append('Yalnız yayımlanan MCP araç tanımları değerlendirildi. Kaynak kod ve gerçek dosya/ağ davranışı bu puanın dışında kaldı.')
    reason = None
    if scan.get('status') != 'completed' or scan.get('analysis_complete') is not True:
        reason = 'Kontrol eksik, sürüyor veya iptal edilmiş; sayısal risk sonucu üretilemez.'
    elif not rows_available:
        reason = 'Bulguların tam listesi mevcut değil; sıfır bulgu varsayılamaz.'
    elif scan.get('profile') == 'dynamic' and not (
        isinstance(scan.get('runtime_report'), dict) and scan['runtime_report'].get('complete') is True and scan['runtime_report'].get('execution_successful') is True
    ):
        reason = 'Davranış testinin tamamlandığına ilişkin kayıt yok; risk puanı hesaplanamadı.'
    elif counts['Unknown']:
        reason = 'En az bir bulgunun önem derecesi eksik veya tanınmıyor; sayısal sonuç üretilemez.'
    contributing = [f['weight'] for f in factors if f['weight'] is not None and f['weight'] > 0]
    strongest = max(contributing, default=0)
    bonus = min(10, 2 * max(0, len(contributing) - 1))
    value = None if reason else min(100, strongest + bonus)
    label = 'Hesaplanamadı' if value is None else 'İncelenen kapsamda 0' if value == 0 else (
        'Kritik öncelik' if value >= 80 else 'Yüksek öncelik' if value >= 50 else 'Orta öncelik' if value >= 25 else 'Düşük öncelik'
    )
    if contract and value==0:label='Araç tanımlarında uyarı bulunmadı'
    ordered=sorted((f for f in factors if (f['weight'] or 0)>0),key=lambda f:(-f['weight'],f['finding_id']))
    for f in factors:f.update(score_contribution=None if value is None else 0,contribution_kind='unscored' if value is None else 'no_addition')
    if value is not None:
        for index,f in enumerate(ordered):
            f['score_contribution']=f['weight'] if index==0 else 2 if index<=5 else 0
            f['contribution_kind']='strongest_finding' if index==0 else 'additional_finding' if index<=5 else 'bonus_cap'
    return {'metric_label':'Araç tanımı önceliği' if contract else 'Risk öncelik puanı','display_value':None if contract and value==0 else value,'show_numeric':value is not None and not (contract and value==0),'behaviour_status':'not_measured' if contract or scan.get('profile')!='dynamic' else 'measured' if value is not None else 'incomplete','policy_version': POLICY_VERSION, 'value': value, 'maximum': 100,
            'label': label, 'status': 'unknown' if reason else 'calculated', 'scope': scope,
            'reason': reason, 'formula': FORMULA, 'weights': dict(WEIGHTS),
            'strongest_weight': strongest, 'additional_findings_bonus': bonus,
            'unique_findings': len(factors), 'duplicates_removed': len(rows) - len(factors),
            'contributing_findings': len(contributing), 'severity_counts': counts,
            'evidence_counts': evidence_counts, 'factors': factors, 'limitations': limitations}
