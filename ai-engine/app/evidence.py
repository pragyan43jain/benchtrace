"""Conservative extraction: source locations are retained, scope is explicit."""
import re
import hashlib
import math
from pathlib import Path
import sexpdata
from pypdf import PdfReader
from .specifications import characteristics


def lexical_embed(text):
    # Offline lexical feature hashing; intentionally NOT called semantic embeddings.
    values=[0.0]*384
    for word in re.findall(r'[\w]+',text.lower()):
        h=int.from_bytes(hashlib.sha256(word.encode()).digest()[:4],'big')
        values[h%384]+=1
    norm=math.sqrt(sum(x*x for x in values)) or 1
    return [x/norm for x in values]


def embed(text):
    import os
    if os.getenv('EMBEDDING_MODE','semantic')=='lexical': return lexical_embed(text)
    from .retrieval import semantic_embed
    return semantic_embed(text)


def document(path):
    if path.suffix.lower()=='.pdf':
        reader=PdfReader(path)
        if len(reader.pages)>300: raise ValueError('PDF exceeds 300 pages')
        pages=[];total=0
        for p in reader.pages:
            text=p.extract_text() or '';total+=len(text)
            if total>2_000_000:raise ValueError('Document exceeds two million extracted characters')
            pages.append(text)
    else: pages=[path.read_text(encoding='utf-8')]
    if sum(map(len,pages))>2_000_000:raise ValueError('Document exceeds two million extracted characters')
    chunks=[];specs=[];structured=[]
    for page,text in enumerate(pages,1):
        structured.extend(characteristics(text,page))
        for offset in range(0,len(text),1200):
            content=text[offset:offset+1400]
            if content.strip(): chunks.append(dict(page=page,content=content,embedding=embed(content)))
        # Preserve whole excerpts rather than asserting a value's electrical meaning.
        for line in text.splitlines():
            if re.search(r'(?i)(0x[0-9a-f]{2}|\b\d+(?:\.\d+)?\s*(?:V|kHz|MHz|ns|µs|mA)\b|SDA|SCL|I2C|UART|SPI)',line):
                specs.append(dict(page=page,excerpt=line[:600],classification='documented excerpt; applicability unverified'))
    if not chunks: raise ValueError('No extractable text; scanned PDFs require OCR (not supported)')
    return dict(kind='document',pages=len(pages),chunks=chunks,specifications=specs[:200],characteristics=structured[:1000],extraction_limits={'specification_excerpts_truncated':len(specs)>200,'characteristics_truncated':len(structured)>1000},summary='\n'.join(pages[0].splitlines()[:8])[:1000],summary_method='Extractive first-page excerpt')


def firmware(text):
    # Strip comments but retain line count; deliberately avoid claiming AST-level understanding.
    clean=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',lambda m:''.join('\n' if c=='\n' else ' ' for c in m[0]),text,flags=re.S)
    defines=dict(re.findall(r'^\s*#define\s+(\w+)\s+(0x[\da-fA-F]+|\d+)\b',clean,re.M))
    def number(v):
        v=defines.get(v.strip(),v.strip())
        try: return int(v,0)
        except ValueError: return None
    findings=[]
    patterns={ 'i2c_begin':r'Wire\.begin\s*\(([^)]*)\)', 'i2c_clock':r'Wire\.setClock\s*\(([^)]*)\)',
               'i2c_address':r'Wire\.beginTransmission\s*\(([^)]*)\)', 'gpio':r'pinMode\s*\(([^)]*)\)',
               'uart_begin':r'Serial\w*\.begin\s*\(([^)]*)\)', 'spi_begin':r'SPI\.begin\s*\(([^)]*)\)', 'blocking_delay':r'delay\s*\(([^)]*)\)'}
    for kind,pattern in patterns.items():
        for m in re.finditer(pattern,clean):
            args=[x.strip() for x in m[1].split(',') if x.strip()]
            findings.append(dict(type=kind,line=clean.count('\n',0,m.start())+1,excerpt=m[0],arguments=args,values=[number(a) for a in args]))
    if 'Wire.beginTransmission' in clean and not re.search(r'\bWire\.begin\s*\(',clean):
        findings.append(dict(type='missing_init',line=1,excerpt='No Wire.begin call found in this file; initialization may occur elsewhere'))
    for m in re.finditer(r'^\s*Wire\.endTransmission\s*\([^)]*\)\s*;',clean,re.M):
        findings.append(dict(type='unchecked_result',line=clean.count('\n',0,m.start())+1,excerpt=m[0].strip()))
    functions=re.findall(r'\b(?:void|int|bool|float|double|uint\d+_t)\s+(\w+)\s*\([^;{}]*\)\s*\{',clean)
    return dict(kind='firmware',method='Bounded Arduino C/C++ pattern analysis; no execution or full AST/type resolution',functions=functions,findings=findings)


def schematic(text):
    tree=sexpdata.loads(text)
    def tag(x): return str(x[0]) if isinstance(x,list) and x else ''
    def children(x,key): return [v for v in x[1:] if tag(v)==key]
    def one(x,key): return next(iter(children(x,key)),None)
    if tag(tree) not in ('kicad_sch','export'): raise ValueError('Expected KiCad schematic or S-expression netlist')
    components=[];nets=[]
    if tag(tree)=='export':
        for c in children(one(tree,'components') or [],'comp'):
            ref=one(c,'ref');value=one(c,'value')
            if ref: components.append(dict(reference=str(ref[1]),value=str(value[1]) if value else ''))
        for n in children(one(tree,'nets') or [],'net'):
            name=one(n,'name');nodes=[]
            for node in children(n,'node'):
                ref,pin=one(node,'ref'),one(node,'pin')
                if ref and pin: nodes.append(dict(reference=str(ref[1]),pin=str(pin[1])))
            nets.append(dict(name=str(name[1]) if name else '',nodes=nodes))
        scope='KiCad exported netlist connectivity; no inferred physical assembly or electrical behavior'
    else:
        for symbol in children(tree,'symbol'):
            props={str(p[1]):str(p[2]) for p in children(symbol,'property') if len(p)>=3}
            if 'Reference' in props: components.append(dict(reference=props['Reference'],value=props.get('Value',''),properties=props))
        for key in ('label','global_label','hierarchical_label'):
            for label in children(tree,key): nets.append(dict(name=str(label[1]),nodes=[]))
        scope='KiCad symbol and label extraction only. Export a KiCad S-expression .net file for reliable pin connectivity.'
    for n in nets: n['power_or_ground']=bool(re.search(r'(?i)(GND|VCC|VDD|3V3|5V)',n['name']))
    return dict(kind='circuit',components=components,nets=nets,scope=scope)


def process(path,options=None):
    path=Path(path)
    ext=path.suffix.lower()
    if ext=='.csv':
        from .signals import analyze_csv
        return analyze_csv(path.read_text(),options)
    if ext in ('.c','.cpp','.h','.hpp','.ino'): return firmware(path.read_text())
    if ext in ('.kicad_sch','.net'): return schematic(path.read_text())
    if ext=='.json':
        import json
        json.loads(path.read_text()) # validation; JSON remains cited text, never instructions
    return document(path)
