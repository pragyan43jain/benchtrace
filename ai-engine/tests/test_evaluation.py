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
