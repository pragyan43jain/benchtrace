#!/usr/bin/env python3
"""One-shot readiness probe for cron or an external monitoring system."""
import json
import os
import sys
import urllib.request
try:
    with urllib.request.urlopen(os.getenv('BENCHTRACE_URL','http://localhost:8080')+'/api/health',timeout=5) as response:
        result=json.load(response)
    if result.get('status')!='ok' or not all(result.get('dependencies',{}).get(x) is True for x in ('database','redis','engine')):
        raise ValueError('Dependencies unavailable')
    print(json.dumps(result))
except Exception as error:
    print('BenchTrace readiness failed: '+str(error),file=sys.stderr)
    sys.exit(1)
