from backend.risk_score import calculate_risk

def finding(id,severity,location=None):return {'finding_id':id,'severity':severity,'source':'static','location':location or {'kind':'logical','path':'/tools/calculate'}}
def scan(rows,**extras):return {'status':'completed','analysis_complete':True,'findings':rows,**extras}
def test_contributions_sum_to_actual_score_and_bonus_is_capped():
 result=calculate_risk(scan([finding(str(i),'High') for i in range(10)]))
 assert result['value']==75 and sum(f['score_contribution'] for f in result['factors'])==75
 assert sum(f['contribution_kind']=='bonus_cap' for f in result['factors'])==4

def test_contract_zero_has_qualitative_display_and_unmeasured_behavior():
 result=calculate_risk(scan([],analysis_kind='remote_contract'))
 assert result['value']==0 and result['display_value'] is None and result['show_numeric'] is False
 assert result['label']=='Araç tanımlarında uyarı bulunmadı' and result['behaviour_status']=='not_measured'

def test_logical_evidence_never_acquires_a_fake_line_number():
 result=calculate_risk(scan([finding('one','High')]))
 assert 'start_line' not in result['factors'][0]['source_refs'][0]

def test_incomplete_factors_are_not_given_completed_contributions():
 result=calculate_risk(scan([finding('one','High')],status='incomplete',analysis_complete=False))
 assert result['value'] is None and result['factors'][0]['score_contribution'] is None

def test_source_ranges_remain_the_actual_ranges():
 result=calculate_risk(scan([finding('one','High',{'kind':'source','path':'server.py','range':{'start_line':12,'end_line':14}})]))
 assert result['factors'][0]['source_refs']==[{'path':'server.py','kind':'source','start_line':12,'end_line':14}]
