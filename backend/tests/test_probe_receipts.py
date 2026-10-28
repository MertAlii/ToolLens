import pytest
from backend import probe_receipts

def test_receipt_bound_to_exact_tested_input_and_result_is_not_mutated():
 original={'status':'connected','tool_count':3,'server_info':{'name':'Example'}}
 issued=probe_receipts.issue('https://example.org/mcp',None,'auto',original)
 original['tool_count']=9
 assert probe_receipts.verified(issued['probe_id'],'https://example.org/mcp',None,'auto')['tool_count']==3
 with pytest.raises(ValueError,match='değişti'):probe_receipts.verified(issued['probe_id'],'https://other.example/mcp',None,'auto')
 with pytest.raises(ValueError,match='değişti'):probe_receipts.verified(issued['probe_id'],'https://example.org/mcp','OTHER_KEY','auto')

def test_receipt_expires_and_failed_results_do_not_issue_id(monkeypatch):
 monkeypatch.setattr(probe_receipts,'monotonic',lambda:100)
 issued=probe_receipts.issue('https://example.org/mcp',None,'sse',{'status':'connected'})
 monkeypatch.setattr(probe_receipts,'monotonic',lambda:401)
 with pytest.raises(ValueError,match='süresi doldu'):probe_receipts.verified(issued['probe_id'],'https://example.org/mcp',None,'sse')
 assert 'probe_id' not in probe_receipts.issue('bad',None,'auto',{'status':'failed'})
