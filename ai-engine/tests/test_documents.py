from pathlib import Path
import pytest
from app.evidence import document,schematic

def pdf_bytes(text):
    escaped=text.replace('\\','\\\\').replace('(','\\(').replace(')','\\)')
    stream=f'BT /F1 12 Tf 50 700 Td ({escaped}) Tj ET'.encode()
    objects=[b'<< /Type /Catalog /Pages 2 0 R >>',b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>',b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',b'<< /Length '+str(len(stream)).encode()+b' >>\nstream\n'+stream+b'\nendstream']
    out=b'%PDF-1.4\n';offsets=[]
    for i,obj in enumerate(objects,1):offsets.append(len(out));out+=f'{i} 0 obj\n'.encode()+obj+b'\nendobj\n'
    offset=len(out);out+=b'xref\n0 6\n0000000000 65535 f \n'
    for x in offsets:out+=f'{x:010d} 00000 n \n'.encode()
    return out+f'trailer\n<< /Root 1 0 R /Size 6 >>\nstartxref\n{offset}\n%%EOF'.encode()

def test_pdf_text_and_citation(tmp_path,monkeypatch):
    monkeypatch.setenv('EMBEDDING_MODE','lexical')
    p=tmp_path/'model.pdf';p.write_bytes(pdf_bytes('SIMULATED sensor I2C address: 0x48'))
    a=document(p)
    assert a['pages']==1 and a['chunks'][0]['page']==1
    assert '0x48' in a['chunks'][0]['content']
    assert len(a['chunks'][0]['embedding'])==384

def test_blank_document_rejected(tmp_path):
    p=tmp_path/'empty.txt';p.write_text('   ')
    with pytest.raises(ValueError,match='No extractable'):document(p)

def test_schematic_scope():
    a=schematic('(kicad_sch (version 20250114)(symbol (property "Reference" "U1")(property "Value" "ESP32"))(label "SDA"))')
    assert a['components'][0]['reference']=='U1'
    assert a['nets'][0]['nodes']==[] and 'not inferred' in a['scope']

def test_schematic_extracts_library_pin_metadata_without_claiming_connectivity():
    text='''(kicad_sch
      (lib_symbols (symbol "Sensor:TMP" (symbol "TMP_0_1"
        (pin input line (name "SDA") (number "1"))
        (pin input line (name "SCL") (number "2")))))
      (symbol (lib_id "Sensor:TMP") (property "Reference" "U2")
        (property "Value" "TMP") (instances (project "demo" (path "/x"
          (reference "U2") (unit 1)))))
      (label "I2C_SDA"))'''
    result=schematic(text)
    component=result['components'][0]
    assert component['library_id']=='Sensor:TMP'
    assert component['pins']==[
        {'number':'1','name':'SDA','electrical_type':'input'},
        {'number':'2','name':'SCL','electrical_type':'input'}]
    assert result['nets'][0]['nodes']==[]
    assert 'not inferred' in result['scope']

def test_structured_characteristics_preserve_limits():
    from app.specifications import characteristics
    r=characteristics('Recommended operating supply voltage: 2.7 to 3.6 V\nAbsolute maximum voltage: 5.5 V\nMaximum I2C clock frequency: 400 kHz\n1 VDD Power supply\n2 SDA Serial data',3)
    assert any(x.get('minimum')==2.7 and x.get('maximum')==3.6 and x['condition']=='recommended_operating' for x in r)
    assert any(x.get('value')==5.5 and x['condition']=='absolute_maximum' for x in r)
    assert any(x.get('value')==400 and x.get('unit')=='kHz' for x in r)
    assert any(x['kind']=='pin' and x['name']=='SDA' for x in r)
    assert all(x['page']==3 and x['excerpt'] for x in r)

def test_parser_subprocess(tmp_path,monkeypatch):
    from app.sandbox import isolated_process
    monkeypatch.setenv('EMBEDDING_MODE','lexical')
    p=tmp_path/'firmware.ino';p.write_text('void setup(){Wire.begin(21,22);}')
    a=isolated_process(p,{})
    assert a['kind']=='firmware' and a['findings'][0]['values']==[21,22]

def test_oversize_extracted_text_is_not_silently_truncated(tmp_path):
    p=tmp_path/'large.txt';p.write_text('x'*2_000_001)
    with pytest.raises(ValueError,match='two million'):document(p)
