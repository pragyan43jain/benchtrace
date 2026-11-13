"""Deterministic evidence ranking. No score is a probability of physical truth."""
import re


def diagnose(files, tests=None, problem=""):
    if problem and re.search(r'\b(?:SPI|UART|CAN|USB)\b',problem,re.I) and not re.search(r'\bI[2²]C\b',problem,re.I):
        return dict(applicable=False,problem=problem,hypotheses=[],summary='Current root-cause rules support I2C investigations. Use waveform analysis for this protocol; no I2C diagnosis was inferred.')
    symptoms=[label for pattern,label in [(r'nack|not ack|no ack','missing acknowledgement'),(r'timeout|timed out','timeout'),(r'stuck|held low','stuck bus'),(r'address','address concern'),(r'pin|wir(?:e|ing)','routing concern')] if re.search(pattern,problem,re.I)]
    addresses=[]; documented=[];nacks=[];acks=[];pins=[];circuits=[];missing=[];logs=[];clocks=[];measured_clocks=[]
    def citation(f,excerpt,**kw): return dict(file_id=f['id'],source=f['name'],excerpt=excerpt,**kw)
    for f in files:
        a=f['analysis']
        for x in a.get('findings',[]):
            if x['type']=='i2c_address' and x['values'] and x['values'][0] is not None:
                idf=x.get('source_api','').startswith('ESP-IDF')
                # Address comparisons against extracted datasheet statements
                # are seven-bit rules; an IDF 10-bit or unspecified width is
                # not comparable and must not create a mismatch hypothesis.
                if not idf or x.get('address_bits')==7:
                    addresses.append((x['values'][0],citation(f,x['excerpt'],line=x['line'])))
            if x['type']=='i2c_begin' and len(x.get('values',[])) in (2,3): pins.append((x.get('values',[]),citation(f,x['excerpt'],line=x['line'])))
            if x['type']=='i2c_clock' and x.get('values') and x['values'][0]:clocks.append((x['values'][0],citation(f,x['excerpt'],line=x['line'])))
            if x['type'] in ('missing_init','pin_conflict'):missing.append(citation(f,x['excerpt'],line=x['line']))
        if a.get('kind')=='circuit':circuits.append((a,citation(f,a['scope'])))
        if f.get('category')=='log' or f['name'].lower().startswith('serial'):
            for c in a.get('chunks',[]):
                for line in c['content'].splitlines():
                    if re.search(r'(?i)(NACK|transaction failed|timeout)',line):logs.append(citation(f,line,page=c['page']))
        if f.get('category')=='datasheet':
            for c in a.get('chunks',[]):
                # Only explicit 7-bit address statements; arbitrary hexadecimal constants are not addresses.
                for m in re.finditer(r'(?i)(?:7[ -]bit\s+)?(?:I2C\s+)?address\s*(?:is|:|=)?\s*(0x[0-9a-f]{2})\b',c['content']):
                    line=c['content'][m.start():].splitlines()[0]
                    if re.search(r'(?i)8[ -]bit',line):continue
                    for value in re.findall(r'0x[0-9a-fA-F]{2}\b',line):
                        documented.append((int(value,16),citation(f,line,page=c['page'])))
        p=a.get('protocols',{}).get('i2c',{})
        if p.get('reliable'):
            if p.get('clock_hz'):measured_clocks.append((p['clock_hz'],citation(f,f"Decoded median SCL clock: {p['clock_hz']:.2f} Hz")))
            for frame in p.get('frames',[]):
                if frame.get('bytes') and frame.get('address') is not None and frame.get('address_width',7)==7:
                    item=(frame['address'],citation(f,f"Decoded 7-bit address 0x{frame['address']:02x}: {'ACK' if frame['bytes'][0]['ack'] else 'NACK'}",time=frame['start']))
                    (acks if frame['bytes'][0]['ack'] else nacks).append(item)
    hypotheses=[]
    safety_notes={
        'address':'When probing the bus, use an instrument rated for the board voltage and avoid shorting adjacent pins. Power down before changing connections.',
        'power':'Live voltage probing can damage equipment or injure the operator. Use an appropriately rated meter and probes, confirm the ground reference, and do not exceed documented limits.',
        'pullups':'Disconnect power before measuring resistance or changing pull-ups. For powered waveform measurements, verify analyzer/probe voltage limits and ground reference first.',
        'pins':'Disconnect power before continuity checks or rewiring. Avoid shorting pins; confirm the board and sensor voltage levels before powered measurements.',
        'timing':'Before attaching probes, confirm voltage limits, ground reference and probe loading are suitable for the board and bus.'}
    def add(key,title,support,against,test,confirm,reject,unknowns):
        hypotheses.append(dict(key=key,title=title,supporting_evidence=support,contradictory_evidence=against,
            evidence_balance=len({x['file_id'] for x in support})-len({x['file_id'] for x in against}),
            ranking_method='Distinct supporting files minus distinct contradicting files; ties ordered by rule key. Not a probability.',
            recommended_test=test,confirms_if=confirm,rejects_if=reject,unknowns=unknowns,
            safety_note=safety_notes[key],status='unverified'))
    mismatch=[];matching=[]
    docs={v for v,c in documented}
    for addr,cite in addresses:
        if docs and addr not in docs: mismatch.append(cite)
        elif addr in docs:matching.append(cite)
    add('address','Firmware targets an incorrect I2C address',mismatch+logs+([c for _,c in documented] if mismatch else [])+[c for v,c in nacks if any(v==a for a,_ in addresses)],
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
    pin_support=list(missing);pin_against=[]
    for circuit,source in circuits:
        controllers={c['reference'] for c in circuit['components'] if 'ESP32' in c.get('value','').upper()}
        expected={}
        for net in circuit['nets']:
            name=net['name'].upper()
            if name not in ('SDA','SCL'):continue
            for node in net['nodes']:
                if node['reference'] in controllers:
                    value=re.fullmatch(r'(?:GPIO)?(\d+)',node['pin'],re.I)
                    if value:expected[name]=int(value[1])
        if len(expected)==2:
            cite=dict(source,excerpt=f"Extracted ESP32 nets: SDA pin {expected['SDA']}, SCL pin {expected['SCL']} from {source['source']}; physical wiring unverified")
            for values,fw_source in pins:
                if len(values)>=2 and None not in values[:2]:
                    (pin_against if values[:2]==[expected['SDA'],expected['SCL']] else pin_support).extend([fw_source,cite])
    add('pins','SDA/SCL routing or initialization is inconsistent',pin_support,pin_against,
        'Compare Wire.begin SDA/SCL arguments with extracted schematic or netlist connections, then check continuity with power disconnected.',
        'Measured wiring differs from configured pins and correcting it restores communication.',
        'Continuity and configured pins agree with the installed wiring.', ['Schematic labels do not prove physical connectivity.'])
    timing_support=[];timing_against=[]
    for configured,fw in clocks:
        for measured,capture in measured_clocks:
            (timing_support if abs(configured-measured)>configured*.15 else timing_against).extend([fw,capture])
    add('timing','Observed I2C clock differs from firmware configuration',timing_support,timing_against,
        'Capture the same firmware transaction with a calibrated timebase and confirm the configured clock against the exact sensor timing specification.',
        'A repeatable clock mismatch or documented timing violation disappears after correcting configuration.',
        'Measured clock matches the configuration and the applicable sensor timing limits.',
        ['A 15% comparison tolerance is a diagnostic heuristic, not an I2C compliance limit. Clock stretching and capture selection can explain differences.'])
    # Recorded results are explicitly attributed to the user, never reclassified as measured by the engine.
    for h in hypotheses:
        for test in tests or []:
            if test.get('rule_key')!=h['key']:continue
            evidence=dict(file_id='test:'+test['id'],source='User-recorded verification test',excerpt=test['observation'],test_id=test['id'])
            if test['outcome'] in ('confirms','supports'):h['supporting_evidence'].append(evidence)
            elif test['outcome']=='rejects':h['contradictory_evidence'].append(evidence)
        h['evidence_balance']=len({x['file_id'] for x in h['supporting_evidence']})-len({x['file_id'] for x in h['contradictory_evidence']})
        h['ranking_method']='Distinct supporting evidence sources minus contradicting sources, including explicitly attributed user test records. Not a probability.'
    hypotheses.sort(key=lambda h:(-h['evidence_balance'],h['key']))
    for i,h in enumerate(hypotheses,1):h['rank']=i
    return dict(applicable=True,problem=problem,symptoms=symptoms,hypotheses=hypotheses,scope='ESP32/Arduino I2C rule-based investigation. All root causes remain hypotheses until a user records verification.',
                evidence_file_count=len(files),unknowns=['No physical hardware was accessed by BenchTrace.'],summary='Address mismatch evidence found.' if mismatch else 'No definitive address mismatch established; follow competing verification tests.')
