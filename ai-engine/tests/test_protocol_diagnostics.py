from app.diagnostics import diagnose

def capture(protocol,decoded):
    return {'id':'capture','name':'capture.csv','analysis':{'protocols':{protocol:decoded}}}

def test_uart_framing_failure_is_hypothesis_not_electrical_claim():
    result=diagnose([capture('uart',{'frames':[{'framing_error':True}],'reliable':False,'warnings':[]})],problem='UART framing failure')
    h=result['hypotheses'][0]
    assert h['key']=='uart_capture' and h['status']=='unverified'
    assert len(h['supporting_evidence'])==1 and not h['contradictory_evidence']
    assert 'eight samples' in h['recommended_test']

def test_spi_insufficient_sampling_requires_recapture():
    result=diagnose([capture('spi',{'frames':[],'reliable':False,'warnings':['Require 3 samples per SPI half-period']})],problem='SPI read failure')
    h=result['hypotheses'][0]
    assert 'Require 3 samples' in h['supporting_evidence'][0]['excerpt']
    assert h['confirms_if'] and h['rejects_if'] and h['safety_note']

def test_good_capture_contradicts_framing_hypothesis_and_preserves_user_attribution():
    result=diagnose([capture('uart',{'frames':[{'value':42}],'reliable':True,'warnings':[]})],tests=[{'id':'test','rule_key':'uart_capture','observation':'Repeated capture has valid stop bits','outcome':'rejects'}],problem='UART wrong data')
    h=result['hypotheses'][0]
    assert not h['supporting_evidence'] and len(h['contradictory_evidence'])==2
    assert h['status']=='unverified' and h['evidence_balance']==-2

def test_uart_without_capture_does_not_invent_fault():
    assert not diagnose([],problem='UART error')['applicable']
