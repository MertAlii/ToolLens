from copy import deepcopy
from pathlib import Path
import re
from backend.presentation import present_finding,present_warning,report_summary,format_date
from backend.reporting import render_report

BASE=Path(__file__).resolve().parents[2]

def sample(**kwargs):
    return {'id':'scan','project_name':'Proje','profile':'rules_only','status':'completed','analysis_complete':True,'findings':[],**kwargs}

def visible_main(report):
    return re.sub(r'<details class="original-record">.*?</details>','',report,flags=re.S)

def test_known_finding_is_plain_turkish_original_is_retained_only_in_details_and_input_unchanged():
    original={'finding_id':'one','rule_id':'SENT-002','severity':'High','source':'static','title':'Unsafe execution from tool input','description':'Tool-controlled input reaches unsafe execution.','remediation':'Replace eval.','location':{'path':'server.py','range':{'start_line':2,'end_line':2}}}
    scan=sample(findings=[original],source_snapshot={'files':{'server.py':'one\ntwo\nthree'}});before=deepcopy(scan)
    result=render_report(scan,BASE);main=visible_main(result)
    assert 'Gelen bilgi bir komut olarak çalıştırılabilir' in main
    assert 'Unsafe execution from tool input' not in main and 'Unsafe execution from tool input' in result
    assert 'href="#finding-1"' in result and 'id="finding-1"' in result and 'server.py · 2. satır' in result
    assert scan==before

def test_report_does_not_invent_line_one_for_logical_locations():
    result=render_report(sample(findings=[{'finding_id':'runtime','rule_id':'SENT-010','severity':'Critical','source':'dynamic','title':'Injection payload executed','location':{'kind':'logical','path':'/tools/calculate/inputSchema/expression'}}]),BASE)
    assert 'Kaynak: /tools/calculate/inputSchema/expression</p>' in result
    assert '/tools/calculate/inputSchema/expression · 1. satır' not in result

def test_remote_zero_report_has_qualitative_contract_outcome_and_no_overall_zero_score():
    result=render_report(sample(analysis_kind='remote_contract'),BASE)
    assert 'Araç tanımlarında uyarı bulunmadı' in result
    assert 'Kaynak kodu ve çalışma davranışı incelenmedi' in result
    assert 'Risk öncelik puanı: 0 / 100' not in result
    assert '0 / 100' not in result
    assert 'Bu kapsamda belirgin risk bulunmadı' not in result

def test_remote_incomplete_is_not_reported_as_clean_contract():
    result=render_report(sample(analysis_kind='remote_contract',status='failed',analysis_complete=False),BASE)
    assert 'Araç tanımı incelemesi tamamlanamadı' in result
    assert 'Araç tanımlarında uyarı bulunmadı' not in result
    assert 'Hesaplanamadı' in result

def test_unknown_rule_has_no_invented_translation_or_claim_and_raw_is_escaped():
    finding={'rule_id':'NEW-999','title':'<script>danger()</script>','description':'Unknown original text','remediation':'Unverified specific recommendation','severity':'Medium','finding_id':'f'}
    result=render_report(sample(project_name='<img src=x onerror=bad>',findings=[finding]),BASE)
    main=visible_main(result)
    assert 'doğrulanmış sade açıklama henüz bulunmuyor' in main
    assert 'Unverified specific recommendation' not in main
    assert '<script>danger()' not in result and '&lt;script&gt;' in result
    assert '<img src=x onerror=bad>' not in result

def test_warning_unknown_original_stays_technical_and_known_warning_is_explained():
    result=render_report(sample(warnings=[{'code':'unknown','message':'ENGLISH ORIGINAL ONLY'},{'code':'dynamic_probe_plan_fallback','message':'PLAN ORIGINAL ONLY'}]),BASE)
    main=visible_main(result)
    assert 'ENGLISH ORIGINAL ONLY' not in main and 'PLAN ORIGINAL ONLY' not in main
    assert 'sabit test sırası' in main
    assert 'ENGLISH ORIGINAL ONLY' in result

def test_istanbul_time_and_missing_or_invalid_dates():
    assert format_date('2026-10-28T17:14:00+00:00')=='28.10.2026 20:14 (Türkiye saati)'
    assert format_date(None)=='Kaydedilmedi'
    assert format_date('<script>')=='Tarih çözümlenemedi'
    result=render_report(sample(started_at='2026-10-28T17:14:00Z'),BASE)
    assert '28.10.2026 20:14 (Türkiye saati)' in result

def test_known_rule_families_have_complete_labels_and_plain_unknown_fallback():
    for number in range(1,17):
        assert all(present_finding({'rule_id':f'SENT-{number:03}'})[key] for key in ('title','why','fix'))
    assert 'sade açıklama' in present_finding({'rule_id':'unrecognized'})['why']


def test_report_lists_actual_factor_contribution_separately_from_severity_weight():
    rows=[{'finding_id':'static','rule_id':'SENT-002','severity':'High','source':'static','location':{'path':'server.py','range':{'start_line':12,'end_line':12}}},
          {'finding_id':'dynamic','rule_id':'SENT-010','severity':'Critical','source':'dynamic','location':{'kind':'logical','path':'/tools/calculate'},'evidence':{'proof':{'verdict':'violation_observed'}}}]
    result=render_report(sample(findings=rows,profile='dynamic',runtime_report={'complete':True,'execution_successful':True}),BASE)
    assert '92 / 100' in result
    assert '<th>Puana katkı</th>' in result
    assert '90 · Temel ağırlık' in result
    assert '2 · Ek bulgu' in result
    assert 'server.py · 12. satır' in result
    assert '/tools/calculate · 1. satır' not in result
