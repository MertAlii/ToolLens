from pathlib import Path
from backend.reporting import render_report
from backend.core import review_packet

BASE=Path(__file__).resolve().parents[2]

def test_report_embeds_logo_and_does_not_give_incomplete_scan_clean_outcome():
    report=render_report({'id':'scan','project_name':'Örnek','status':'failed','analysis_complete':False,'findings':[]},BASE)
    assert 'data:image/png;base64,' in report
    assert 'Sonuç için bilgi yetersiz' in report
    assert 'güvenli kullanım onayı değildir' in report
    assert 'Yazdır / PDF olarak kaydet' in report

def test_completed_zero_findings_report_states_scope_without_unconditional_approval():
    report=render_report({'id':'s','status':'completed','analysis_complete':True,'findings':[]},BASE)
    assert 'Bu kapsamda belirgin risk bulunmadı' in report
    assert 'güvenlik sertifikası değildir' in report

def test_zero_findings_packet_contains_bounded_real_source_and_honest_counts():
    files={'server.py':'@mcp.tool()\ndef calculate(): return 2\n'+'# example\n'*2000,'data.json':'{}'}
    packet=review_packet('s',[],files)
    assert packet['total_source_files']==2
    assert packet['provided_source_files']==1
    assert len(packet['sources'][0]['snippet'])<=4000
    assert packet['sources'][0]['range']['end_line']<2000
