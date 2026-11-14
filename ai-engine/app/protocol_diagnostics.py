"""Capture-grounded UART/SPI investigation; no electrical root cause claims."""
def diagnose_protocol(files, tests, problem, protocol):
    support, against = [], []
    for f in files:
        decoded=f.get('analysis',{}).get('protocols',{}).get(protocol)
        if not decoded:
            continue
        warnings=decoded.get('warnings',[])
        frames=decoded.get('frames',[])
        citation=lambda text: dict(file_id=f['id'],source=f['name'],excerpt=text)
        support.extend(citation('Decoder warning: '+w) for w in warnings)
        if protocol=='uart' and any(frame.get('framing_error') for frame in frames):
            support.append(citation('UART decoder observed a low stop-bit sample under the selected 8N1/baud settings; configuration and waveform require verification.'))
        if decoded.get('reliable') and frames:
            against.append(citation('Complete frames decoded without reported boundary or sampling errors under the selected settings. This does not verify payload correctness.'))
    if not support and not against:
        return dict(applicable=False,problem=problem,hypotheses=[],summary='No selected '+protocol.upper()+' capture evidence supports an investigation.')
    key=protocol+'_capture'
    if protocol=='uart':
        title='UART configuration or capture quality may explain framing failures'
        test='Compare the configured baud, polarity and 8N1 format with both endpoints. Recapture RX with at least eight samples per bit and inspect start/stop bits; change only one setting at a time.'
        confirms='The original settings reproduce framing errors and a documented setting correction removes them in repeated captures.'
        rejects='The original documented settings repeatedly decode correct start/stop bits at sufficient sampling; investigate payload and application behavior separately.'
    else:
        title='SPI capture boundaries or selected mode may explain incomplete decoding'
        test='Verify CPOL, CPHA, word width and active-low chip select against firmware and the exact device documentation. Capture complete CS assertions and at least three samples per clock half-period, then compare the same transaction.'
        confirms='A repeatable boundary or mode mismatch is established against documentation and correcting it restores complete expected words.'
        rejects='Complete transactions decode with the documented mode and width; investigate payload/device response separately.'
    for record in tests or []:
        if record.get('rule_key')==key:
            cite=dict(file_id='test:'+record['id'],source='User-recorded verification test',excerpt=record['observation'],test_id=record['id'])
            if record['outcome'] in ('supports','confirms'):support.append(cite)
            elif record['outcome']=='rejects':against.append(cite)
    hypothesis=dict(key=key,title=title,rank=1,status='unverified',supporting_evidence=support,contradictory_evidence=against,
        evidence_balance=len({x['file_id'] for x in support})-len({x['file_id'] for x in against}),
        ranking_method='Distinct supporting sources minus contradicting sources. One capture-quality hypothesis; not a probability or a competing electrical diagnosis.',
        recommended_test=test,confirms_if=confirms,rejects_if=rejects,
        unknowns=['Decoder settings may differ from the actual endpoint configuration.','A capture decoding failure does not establish an electrical fault.'],
        safety_note='Use isolated low-voltage hardware and probes rated for its voltage. Disconnect power before changing connections.')
    return dict(applicable=True,problem=problem,hypotheses=[hypothesis],evidence_file_count=len(files),scope=protocol.upper()+' capture-quality investigation only',unknowns=hypothesis['unknowns'],summary=title)
