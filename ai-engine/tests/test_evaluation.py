import json
from pathlib import Path
import pytest
from app.evidence import firmware
from app.diagnostics import diagnose
SCENARIOS=json.loads((Path(__file__).parents[1]/'evaluation/scenarios.json').read_text())
@pytest.mark.parametrize('case',SCENARIOS,ids=[x['name'] for x in SCENARIOS])
def test_fixed_diagnostic_scenarios(case):
    files=[{'id':'fw','name':'firmware.ino','category':'firmware','analysis':firmware(case['firmware'])},
           {'id':'doc','name':'datasheet.txt','category':'datasheet','analysis':{'chunks':[{'page':1,'content':case['document']}]}}]
    result=diagnose(files)
    if case['expected_first']:assert result['hypotheses'][0]['key']==case['expected_first']
    address=next(h for h in result['hypotheses'] if h['key']=='address')
    assert bool(address['contradictory_evidence'])==case['expected_contradiction']
    for h in result['hypotheses']:
        assert h['status']=='unverified' and h['recommended_test'] and h['confirms_if'] and h['rejects_if'] and h['unknowns']
        assert 'probability' in h['ranking_method']
        for e in h['supporting_evidence']+h['contradictory_evidence']:
            assert e['file_id'] in ('fw','doc')
            assert e['excerpt'] in case['firmware'] or e['excerpt'] in case['document'] or e['excerpt'].startswith('No Wire.begin')

def test_problem_scope_does_not_invent_i2c_fault_for_spi():
    r=diagnose([],problem='SPI sensor reads incorrect data')
    assert r['applicable'] is False and not r['hypotheses']

def test_reported_symptoms_are_preserved_without_measurement_claim():
    r=diagnose([],problem='I2C sensor times out and returns NACK at address 0x48')
    assert 'missing acknowledgement' in r['symptoms']
    assert 'address concern' in r['symptoms']
    assert all(not h['supporting_evidence'] for h in r['hypotheses'])

def test_electrical_recommendations_include_relevant_safety_limits():
    result=diagnose([{'id':'fw','name':'firmware.ino','analysis':firmware('Wire.beginTransmission(0x49); Wire.endTransmission();')}])
    hypotheses={h['key']:h for h in result['hypotheses']}
    power=hypotheses['power']['assessment']['recommended_test'] if 'assessment' in hypotheses['power'] else hypotheses['power']['recommended_test']
    pullups=hypotheses['pullups']['assessment']['recommended_test'] if 'assessment' in hypotheses['pullups'] else hypotheses['pullups']['recommended_test']
    pins=hypotheses['pins']['assessment']['recommended_test'] if 'assessment' in hypotheses['pins'] else hypotheses['pins']['recommended_test']
    assert 'isolated' in power and 'Do not probe mains' in power
    assert 'power removed' in pullups
    assert 'power disconnected' in pins
