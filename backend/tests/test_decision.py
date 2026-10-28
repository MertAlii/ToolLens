from backend.decision import classify_decision, summarize_decisions
from backend.core import Workbench


def test_four_boxes_use_impact_and_evidence_separately():
    human={'decision':'confirmed','note':'Kaynak incelendi.'}
    cases=[('High',human,'fix_now'),('High',None,'verify_now'),('Low',human,'plan_fix'),('Low',None,'observe')]
    for impact,annotation,box in cases:
        result=classify_decision({'impact':impact,'annotation':annotation})
        assert result['box']==box


def test_ai_or_static_confirmed_is_not_runtime_proof():
    result=classify_decision({'impact':'Critical','status':'confirmed','review':{'status':'confirmed','reviewed':True}})
    assert result['box']=='verify_now'
    assert result['evidence_sources']==[]


def test_provenance_runtime_proof_and_human_are_labeled():
    finding={'impact':'High','annotation':{'decision':'confirmed','note':'Kaynak incelendi.'},'provenance':[{'evidence':{'proof':{'verdict':'violation_observed'}}}]}
    result=classify_decision(finding)
    assert result['box']=='fix_now'
    assert result['evidence_sources']==['runtime_proof','human_assessment']


def test_missing_impact_is_not_guessed_from_severity():
    assert classify_decision({'severity':'Critical'})['box']=='unclassified'


def test_unreasoned_human_marker_does_not_upgrade_evidence():
    assert classify_decision({'impact':'High','annotation':{'decision':'confirmed'}})['box']=='verify_now'


def test_summary_preserves_denominator_and_version():
    rows=[{'impact':'High'},{'impact':'Low'},{}]
    result=summarize_decisions(rows)
    assert result['policy_version']=='tl-decision-v1'
    assert result['total']==sum(result['counts'].values())==3


def test_annotation_updates_scan_and_export_decision_without_mutating_origin(tmp_path):
    wb=Workbench(tmp_path)
    original={'findings':[{'finding_id':'f','impact':'High','title':'risk'}]}
    try:
        wb.store.put('scan',{'id':'s','project_id':'p','profile':'rules_only','status':'completed','analysis_complete':True,'findings':original['findings'],'engine_report':original})
        assert wb.scan('s')['decision_summary']['counts']['verify_now']==1
        wb.annotate('s','f','confirmed','Reviewed by user')
        result=wb.scan('s')
        assert result['decision_summary']['counts']['fix_now']==1
        assert result['engine_report']==original
        html=wb.export_html(result)
        assert 'Dörtlü Karar Kutusu' in html
        assert 'tl-decision-v1' in html
    finally:
        wb.close()
