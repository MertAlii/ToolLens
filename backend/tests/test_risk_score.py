from copy import deepcopy

import pytest

from backend.risk_score import calculate_risk


def scan(*findings, **overrides):
    return {'status': 'completed', 'analysis_complete': True, 'profile': 'rules_only',
            'findings': list(findings), **overrides}


def finding(severity='High', key='one', **extra):
    return {'finding_id': key, 'severity': severity, 'source': 'static', **extra}


@pytest.mark.parametrize('status', ['queued', 'running', 'incomplete', 'cancelled', 'failed'])
def test_unfinished_zero_findings_is_unknown(status):
    result = calculate_risk(scan(status=status))
    assert result['value'] is None and result['status'] == 'unknown'


def test_false_analysis_complete_or_missing_full_findings_cannot_produce_zero():
    assert calculate_risk(scan(analysis_complete=False))['value'] is None
    assert calculate_risk({'status': 'completed', 'analysis_complete': True, 'summary': {'total': 0}})['value'] is None


def test_zero_is_scoped_and_does_not_claim_safety():
    result = calculate_risk(scan())
    assert result['value'] == 0 and result['label'] == 'İncelenen kapsamda 0'
    assert result['scope'] == 'source_only' and result['policy_version'] == 'toollens-risk-v1'
    assert any('sertifikası değildir' in text for text in result['limitations'])


def test_highest_severity_dominates_and_volume_bonus_is_bounded():
    assert calculate_risk(scan(finding('Critical')))['value'] == 90
    assert calculate_risk(scan(finding('High')))['value'] == 65
    assert calculate_risk(scan(finding('Medium')))['value'] == 35
    assert calculate_risk(scan(finding('Informational')))['value'] == 0
    lows = [finding('Low', str(i)) for i in range(100)]
    assert calculate_risk(scan(*lows))['value'] == 20
    assert calculate_risk(scan(finding('Critical', 'critical'), *lows))['value'] == 100


def test_duplicate_ids_are_not_counted_and_order_does_not_change_result():
    a, b = finding('Medium'), finding('High')
    result = calculate_risk(scan(a, b, finding('Low', 'two')))
    assert result['value'] == 67 and result['duplicates_removed'] == 1
    assert result == calculate_risk(scan(finding('Low', 'two'), b, a))


def test_missing_ids_use_stable_source_location_identity():
    row = {'severity': 'High', 'source': 'static', 'rule_id': 'SENT-002', 'location': {'path': 'a.py', 'line': 2}}
    result = calculate_risk(scan(row, deepcopy(row)))
    assert result['value'] == 65 and result['unique_findings'] == 1


def test_anonymous_findings_without_identity_are_not_silently_collapsed():
    result = calculate_risk(scan({'severity': 'High'}, {'severity': 'High'}))
    assert result['value'] == 67 and result['unique_findings'] == 2


def test_duplicate_conflicting_rule_metadata_is_order_independent():
    a = finding('High', rule_id='SENT-002')
    b = finding('Medium', rule_id='SENT-001')
    assert calculate_risk(scan(a, b)) == calculate_risk(scan(b, a))


def test_unknown_or_conflicting_missing_severity_remains_unknown():
    assert calculate_risk(scan(finding('Unexpected')))['value'] is None
    assert calculate_risk(scan(finding('High'), finding(None)))['value'] is None


def test_runtime_proof_is_separate_from_ai_human_or_dynamic_origin():
    rows = [finding('High', 'static', review={'status': 'confirmed'}, annotation={'decision': 'confirmed', 'note': 'Reviewed'}),
            finding('High', 'dynamic', source='dynamic'),
            finding('High', 'proven', source='dynamic', evidence={'proof': {'verdict': 'violation_observed'}})]
    result = calculate_risk(scan(*rows))
    assert result['evidence_counts']['runtime_proven'] == 1
    assert result['evidence_counts']['unverified_dynamic'] == 1
    assert result['evidence_counts']['static'] == 1
    assert result['value'] == 69


def test_dynamic_incomplete_report_cannot_be_scored_even_if_scan_claims_complete():
    for runtime in (None, {}, {'complete': False}, {'complete': True}, {'complete': True,'execution_successful':False}):
        assert calculate_risk(scan(finding(), profile='dynamic', runtime_report=runtime))['value'] is None
    assert calculate_risk(scan(finding(), profile='dynamic', runtime_report={'complete': True,'execution_successful':True}))['value'] == 65


def test_http_catalog_has_contract_only_scope_not_source_or_runtime_safety():
    result = calculate_risk(scan(finding('Medium', source='remote_contract'), analysis_kind='remote_contract'))
    assert result['value'] == 35 and result['scope'] == 'contract_only'
    assert result['evidence_counts']['contract'] == 1
    assert any('gerçek dosya/ağ davranışı' in text for text in result['limitations'])
    assert calculate_risk(scan(analysis_kind='remote_contract'))['scope'] == 'contract_only'


def test_false_positive_note_does_not_silently_remove_original_finding_or_mutate_input():
    raw = scan(finding(annotation={'decision': 'false_positive', 'note': 'Example fixture'}))
    before = deepcopy(raw)
    assert calculate_risk(raw)['value'] == 65
    assert raw == before
