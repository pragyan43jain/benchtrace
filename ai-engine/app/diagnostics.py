"""Deterministic evidence ranking. No score is a probability of physical truth."""
import re


def diagnose(files):
    addresses=[]; documented=[];nacks=[];acks=[];pins=[];circuits=[];missing=[]
    def citation(f,excerpt,**kw): return dict(file_id=f['id'],source=f['name'],excerpt=excerpt,**kw)
    for f in files:
        a=f['analysis']
        for x in a.get('findings',[]):
            if x['type']=='i2c_address' and x['values'] and x['values'][0] is not None:
                addresses.append((x['values'][0],citation(f,x['excerpt'],line=x['line'])))
            if x['type']=='i2c_begin': pins.append((x.get('values',[]),citation(f,x['excerpt'],line=x['line'])))
            if x['type']=='missing_init':missing.append(citation(f,x['excerpt'],line=x['line']))
        if a.get('kind')=='circuit':circuits.append((a,citation(f,a['scope'])))
        if f.get('category')=='datasheet':
            for c in a.get('chunks',[]):
                # Only explicit 7-bit address statements; arbitrary hexadecimal constants are not addresses.
                for m in re.finditer(r'(?i)(?:7[ -]bit\s+)?(?:I2C\s+)?address\s*(?:is|:|=)?\s*(0x[0-9a-f]{2})\b',c['content']):
                    documented.append((int(m[1],16),citation(f,c['content'],page=c['page'])))
        p=a.get('protocols',{}).get('i2c',{})
        if p.get('reliable'):
            for frame in p.get('frames',[]):
                if frame.get('bytes'):
                    item=(frame.get('address'),citation(f,f"Decoded address 0x{frame['address']:02x}: {'ACK' if frame['bytes'][0]['ack'] else 'NACK'}",time=frame['start']))
                    (acks if frame['bytes'][0]['ack'] else nacks).append(item)
    hypotheses=[]
    def add(key,title,support,against,test,confirm,reject,unknowns):
        hypotheses.append(dict(key=key,title=title,supporting_evidence=support,contradictory_evidence=against,
            evidence_balance=len({x['file_id'] for x in support})-len({x['file_id'] for x in against}),
            ranking_method='Distinct supporting files minus distinct contradicting files; ties ordered by rule key. Not a probability.',
            recommended_test=test,confirms_if=confirm,rejects_if=reject,unknowns=unknowns,status='unverified'))
    mismatch=[];matching=[]
    docs={v for v,c in documented}
    for addr,cite in addresses:
        if docs and addr not in docs: mismatch.append(cite)
        elif addr in docs:matching.append(cite)
    add('address','Firmware targets an incorrect I2C address',mismatch+([c for _,c in documented] if mismatch else [])+[c for v,c in nacks if any(v==a for a,_ in addresses)],
        matching+[c for v,c in acks if any(v==a for a,_ in addresses)],
        'Confirm the exact sensor variant and address straps against its uploaded datasheet, then change only the firmware address and capture the same transaction.',
        'The corrected documented address ACKs and repeat communication succeeds while the old address NACKs.',
        'The original address ACKs reliably and is valid for the installed part.',
        ['Datasheet applicability and actual address straps need physical verification.'])
    add('power','Sensor supply or ground is missing or incompatible',[c for _,c in nacks],[c for _,c in acks],
        'On a low-voltage isolated bench setup, measure sensor VDD relative to sensor GND and compare with the exact datasheet. Do not probe mains or unknown high-voltage circuits.',
        'Measured supply is absent or outside the applicable documented range and correcting it restores communication.',
        'Supply and ground remain within specification during the failure.', ['No supply voltage measurement has been established by a digital bus capture.'])
    add('pullups','I2C pull-ups or bus loading prevent valid logic levels',[c for _,c in nacks],[c for _,c in acks],
        'Capture analog SDA/SCL at the sensor. Compare idle levels and rise times to the applicable bus and sensor specifications; inspect pull-ups with power removed.',
        'Measured rise times or voltage levels violate documented limits and a corrected pull-up network restores ACKs.',
        'Analog levels and rise times meet applicable limits throughout the failed transaction.', ['Digital NACKs alone cannot establish missing pull-ups.'])
    add('pins','SDA/SCL routing or initialization is inconsistent',missing,[],
        'Compare Wire.begin SDA/SCL arguments with exported schematic nets, then check continuity with power disconnected.',
        'Measured wiring differs from configured pins and correcting it restores communication.',
        'Continuity and configured pins agree with the installed wiring.', ['Schematic labels do not prove physical connectivity.'])
    hypotheses.sort(key=lambda h:(-h['evidence_balance'],h['key']))
    for i,h in enumerate(hypotheses,1):h['rank']=i
    return dict(hypotheses=hypotheses,scope='ESP32/Arduino I2C rule-based investigation. All root causes remain hypotheses until a user records verification.',
                evidence_file_count=len(files),unknowns=['No physical hardware was accessed by BenchTrace.'],summary='Address mismatch evidence found.' if mismatch else 'No definitive address mismatch established; follow competing verification tests.')
