"""Conservative extraction: source locations are retained, scope is explicit."""
import re
import hashlib
import math
from pathlib import Path
import sexpdata
from pypdf import PdfReader
from .specifications import characteristics
from .retrieval import embedding_version


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
    return dict(kind='document',embedding_version=embedding_version(),pages=len(pages),chunks=chunks,specifications=specs[:200],characteristics=structured[:1000],extraction_limits={'specification_excerpts_truncated':len(specs)>200,'characteristics_truncated':len(structured)>1000},summary='\n'.join(pages[0].splitlines()[:8])[:1000],summary_method='Extractive first-page excerpt')


def firmware(text):
    # Strip comments but retain line count; deliberately avoid claiming AST-level understanding.
    clean=re.sub(r'//[^\n]*|/\*.*?\*/|"(?:\\.|[^"\\])*"',lambda m:''.join('\n' if c=='\n' else ' ' for c in m[0]),text,flags=re.S)
    numeric_or_alias=r'(?:0x[\da-fA-F]+|\d+|[A-Za-z_]\w*)'
    defines=dict(re.findall(r'^\s*#define\s+(\w+)\s+('+numeric_or_alias+r')\b',clean,re.M))
    defines.update(dict(re.findall(r'\b(?:constexpr|const)\s+(?:unsigned\s+)?(?:int|uint\d+_t|byte|auto)\s+(\w+)\s*=\s*('+numeric_or_alias+r')\s*;',clean)))
    def number(v):
        v=v.strip()
        for _ in range(8):
            if v not in defines:break
            v=defines[v]
        gpio=re.fullmatch(r'GPIO_NUM_(\d+)',v)
        if gpio:return int(gpio[1])
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
    # Recognize the bounded ESP-IDF designated-initializer form. This does not
    # follow handles or establish that the configured bus/device is used.
    for m in re.finditer(r'\bi2c_master_bus_config_t\s+\w+\s*=\s*\{([^{}]*)\}',clean,re.S):
        fields={name:match.group(1).strip() for name in ('sda_io_num','scl_io_num')
                if (match:=re.search(r'\.'+name+r'\s*=\s*([\w]+)',m[1]))}
        if len(fields)==2:
            args=[fields['sda_io_num'],fields['scl_io_num']]
            findings.append(dict(type='i2c_begin',line=clean.count('\n',0,m.start())+1,
                                 excerpt=m[0][:500],arguments=args,values=[number(x) for x in args],
                                 source_api='ESP-IDF i2c_master_bus_config_t designated initializer'))
    for m in re.finditer(r'\bi2c_device_config_t\s+\w+\s*=\s*\{([^{}]*)\}',clean,re.S):
        length=re.search(r'\.dev_addr_length\s*=\s*I2C_ADDR_BIT_LEN_(7|10)\b',m[1])
        address_bits=int(length[1]) if length else None
        for field,kind in (('device_address','i2c_address'),('scl_speed_hz','i2c_clock')):
            match=re.search(r'\.'+field+r'\s*=\s*([\w]+)',m[1])
            if match:
                value=match.group(1)
                finding=dict(type=kind,line=clean.count('\n',0,m.start())+1,
                             excerpt=m[0][:500],arguments=[value],values=[number(value)],
                             source_api='ESP-IDF i2c_device_config_t designated initializer')
                if kind=='i2c_address':finding['address_bits']=address_bits
                findings.append(finding)
    if 'Wire.beginTransmission' in clean and not re.search(r'\bWire\.begin\s*\(',clean):
        findings.append(dict(type='missing_init',line=1,excerpt='No Wire.begin call found in this file; initialization may occur elsewhere'))
    for m in re.finditer(r'^\s*Wire\.endTransmission\s*\([^)]*\)\s*;',clean,re.M):
        findings.append(dict(type='unchecked_result',line=clean.count('\n',0,m.start())+1,excerpt=m[0].strip()))
    # Flag common blocking I2C reads without suggesting runtime certainty.
    for m in re.finditer(r'\bwhile\s*\([^)]*Wire\.available\s*\([^)]*\)[^)]*\)',clean):
        tail=clean[m.end():m.end()+500]
        if not re.search(r'\b(?:millis|micros)\s*\(|\btimeout\b|\bdeadline\b',tail,re.I):
            findings.append(dict(type='unbounded_i2c_wait',line=clean.count('\n',0,m.start())+1,excerpt=m[0],explanation='A loop waits on Wire.available without an obvious nearby timeout. Static pattern only: another exit path or timeout helper may exist outside this window.'))
    # Lightweight error-path checks stay advisory and retain the triggering line.
    for m in re.finditer(r'Wire\.requestFrom\s*\(([^)]*)\)',clean):
        tail=clean[m.end():m.end()+500]
        if 'Wire.available' not in tail:
            findings.append(dict(type='unchecked_i2c_read',line=clean.count('\n',0,m.start())+1,excerpt=m[0],explanation='A requestFrom call appears without a nearby Wire.available check. Verify the returned byte count and timeout behavior; this bounded scan does not follow control flow.'))
    for m in re.finditer(r'Wire\.endTransmission\s*\([^)]*\)',clean):
        tail=clean[m.end():m.end()+180]
        if re.match(r'\s*;',tail) and not re.search(r'if\s*\(\s*Wire\.endTransmission',clean[max(0,m.start()-100):m.start()]):
            line=clean.count('\n',0,m.start())+1
            if not any(f.get('type')=='unchecked_result' and f.get('line')==line for f in findings):
                findings.append(dict(type='unchecked_result',line=line,excerpt=m[0],explanation='The endTransmission status may be discarded; inspect return-code handling around this call.'))
    explanations={
        'i2c_begin':'Requests I2C bus pin configuration using a recognized Arduino or ESP-IDF form. Static values do not prove that initialization executes successfully.',
        'i2c_address':'Targets or configures this I2C device address. Compare the seven-bit address with the exact part and address straps.',
        'i2c_clock':'Requests an I2C bus clock rate. Actual clock and clock stretching must be checked in a capture.',
        'gpio':'Configures a pin mode. Its runtime path and board-specific electrical suitability are not established.',
        'uart_begin':'Requests serial initialization; compare baud and frame format with the capture and connected device.',
        'spi_begin':'Initializes the SPI peripheral; pin mapping and transaction mode may be configured elsewhere.',
        'unbounded_i2c_wait':'A loop waits on Wire.available without an obvious nearby timeout; static pattern does not establish reachable blocking behavior.',
        'unchecked_i2c_read':'A requestFrom call has no nearby available-byte check. Verify returned byte count and timeout handling; this scan does not follow control flow.',
        'blocking_delay':'Blocks this task for the specified delay. Impact on deadlines depends on task scheduling and runtime paths.',
        'unchecked_result':'The endTransmission return value is discarded here, so this call does not report transaction failure to its caller.',
        'missing_init':'No local initialization call was found. Inspect other files before concluding initialization is absent.'}
    extra=[]
    for finding in findings:
        finding['explanation']=explanations.get(finding['type'],'Static pattern observation; verify in context.')
        values=finding.get('values',[])
        if finding['type']=='i2c_begin' and len(values) in (2,3) and values[0] is not None and values[0]==values[1]:
            extra.append(dict(type='pin_conflict',line=finding['line'],excerpt=finding['excerpt'],explanation='The recognized master-mode call assigns SDA and SCL to the same pin. Verify the intended Wire.begin overload and board mapping.'))
        if finding['type']=='i2c_address' and values and values[0] is not None:
            width=finding.get('address_bits',7)
            if width in (7,10) and not 0<=values[0]<(1<<width):
                extra.append(dict(type='invalid_address',line=finding['line'],excerpt=finding['excerpt'],explanation=f'The literal target is outside the configured {width}-bit address range. Verify the intended address representation.'))
    findings.extend(extra)
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
        # KiCad embeds library symbol definitions in the schematic. Pin
        # metadata alone does not establish connectivity; the bounded geometric
        # pass below relates pin endpoints to wires, labels, and junctions.
        libraries={}
        lib_root=one(tree,'lib_symbols')
        for definition in children(lib_root or [],'symbol'):
            lib_id=str(definition[1]) if len(definition)>1 else ''
            pins=[]
            for part in children(definition,'symbol'):
                part_name=str(part[1]) if len(part)>1 else ''
                unit_match=re.search(r'_(\d+)_\d+$',part_name)
                unit=int(unit_match[1]) if unit_match else None
                for pin in children(part,'pin'):
                    name,number,position=one(pin,'name'),one(pin,'number'),one(pin,'at')
                    if name and number and len(name)>1 and len(number)>1:
                        kind=str(pin[1]) if len(pin)>1 else ''
                        local_at=None
                        if position and len(position)>=3:
                            try: local_at=(float(position[1]),float(position[2]))
                            except (TypeError,ValueError): pass
                        pins.append(dict(number=str(number[1]),name=str(name[1]),electrical_type=kind,
                                         unit=unit,local_at=local_at))
            libraries[lib_id]=pins
        # Connectivity for the root sheet only. Coordinates and symbol pins
        # follow KiCad's S-expression format. Mirrored symbols and hierarchy
        # are deliberately excluded until their transforms are implemented.
        wires=[]
        for wire in children(tree,'wire'):
            points=[]
            pts=one(wire,'pts')
            for point in children(pts or [],'xy'):
                if len(point)>=3:
                    try: points.append((float(point[1]),float(point[2])))
                    except (TypeError,ValueError): pass
            wires.extend((points[i],points[i+1]) for i in range(len(points)-1))
        anchors=[]
        labels=[]
        unlocated_labels=[]
        for key,scope_name in (('label','local'),('global_label','global'),('hierarchical_label','hierarchical')):
            for label in children(tree,key):
                pos=one(label,'at')
                if len(label)>1 and pos and len(pos)>=3:
                    try:
                        point=(float(pos[1]),float(pos[2])); name=str(label[1])
                        anchors.append((point,('label',name)))
                        labels.append((point,name,scope_name))
                    except (TypeError,ValueError): unlocated_labels.append(name)
                elif len(label)>1:
                    unlocated_labels.append(str(label[1]))
        junctions=[]
        for junction in children(tree,'junction'):
            pos=one(junction,'at')
            if pos and len(pos)>=3:
                try:
                    point=(float(pos[1]),float(pos[2])); junctions.append(point)
                    anchors.append((point,('junction',len(junctions))))
                except (TypeError,ValueError): pass
        def get_netlist_pin_position(symbol, pin):
            pos=one(symbol,'at')
            if not pos or len(pos)<4 or not pin.get('local_at'): return None
            if one(symbol,'mirror'): return None
            try:
                origin=(float(pos[1]),float(pos[2])); angle=float(pos[3])%360
                x,y=pin['local_at']
            except (TypeError,ValueError): return None
            # KiCad schematic coordinates use a downward-positive sheet Y axis.
            # The supported rotations are the format's right angles.
            if angle==0: dx,dy=x,y
            elif angle==90: dx,dy=y,-x
            elif angle==180: dx,dy=-x,-y
            elif angle==270: dx,dy=-y,x
            else: return None
            return (origin[0]+dx,origin[1]+dy)
        component_pin_anchors=[]
        for symbol in children(tree,'symbol'):
            props={str(p[1]):str(p[2]) for p in children(symbol,'property') if len(p)>=3}
            lib_id=one(symbol,'lib_id')
            if 'Reference' in props:
                library_id=str(lib_id[1]) if lib_id and len(lib_id)>1 else ''
                try: unit=int(one(symbol,'unit')[1])
                except (TypeError,IndexError): unit=1
                pins=[p.copy() for p in libraries.get(library_id,[]) if p.get('unit') in (0,unit)]
                for pin in pins:
                    point=get_netlist_pin_position(symbol,pin)
                    if point is not None:
                        pin['sheet_position']=[round(point[0],4),round(point[1],4)]
                        component_pin_anchors.append((point,('pin',props['Reference'],pin['number'])))
                mirror=one(symbol,'mirror')
                position_supported=bool(pins) and all('sheet_position' in p for p in pins)
                components.append(dict(reference=props['Reference'],value=props.get('Value',''),properties=props,
                                       library_id=library_id,pins=[{k:v for k,v in p.items() if k not in ('unit','local_at')} for p in pins],
                                       pin_positions_supported=position_supported and not bool(mirror)))
                # Power symbols name a net through their value and single pin.
                if props['Reference'].startswith('#PWR') and props.get('Value') and len(pins)==1:
                    point=get_netlist_pin_position(symbol,pins[0])
                    if point is not None:
                        anchors.append((point,('label',props['Value'])))
                        labels.append((point,props['Value'],'power_symbol'))
        anchors.extend(component_pin_anchors)
        # Use a disjoint-set over wire endpoint coordinates.  Wires connect at
        # endpoints, pin/label locations and explicit junctions; interior-to-
        # interior crossings remain separate when no junction is drawn.
        endpoints=[point for segment in wires for point in segment]
        points=[]; seen_points=set()
        def point_key(point): return (round(point[0],4),round(point[1],4))
        for point in endpoints+[p for p,_ in anchors]:
            key=point_key(point)
            if key not in seen_points:
                seen_points.add(key); points.append(key)
        parent=list(range(len(points)))
        def find(index):
            while parent[index]!=index:
                parent[index]=parent[parent[index]]; index=parent[index]
            return index
        def union(a,b):
            a,b=find(a),find(b)
            if a!=b: parent[b]=a
        indices={point:i for i,point in enumerate(points)}
        horizontal={}; vertical={}; unsupported_wire_geometry=False
        for a,b in wires:
            if abs(a[1]-b[1])<=1e-4:
                horizontal.setdefault(round(a[1],4),[]).append((min(a[0],b[0]),max(a[0],b[0])))
            elif abs(a[0]-b[0])<=1e-4:
                vertical.setdefault(round(a[0],4),[]).append((min(a[1],b[1]),max(a[1],b[1])))
            else:
                unsupported_wire_geometry=True
        horizontal_points={}; vertical_points={}
        for key in points:
            horizontal_points.setdefault(key[1],[]).append(key[0])
            vertical_points.setdefault(key[0],[]).append(key[1])
        for values in list(horizontal_points.values())+list(vertical_points.values()): values.sort()
        from bisect import bisect_left,bisect_right
        connection_operations=0; connectivity_limit_hit=len(wires)>10_000 or len(anchors)>20_000
        for a,b in ([] if connectivity_limit_hit else wires):
            if abs(a[1]-b[1])<=1e-4:
                ys=round(a[1],4); row=horizontal_points.get(ys,[])
                lo=bisect_left(row,min(a[0],b[0])-1e-4); hi=bisect_right(row,max(a[0],b[0])+1e-4)
                candidates=[(x,ys) for x in row[lo:hi]]
            elif abs(a[0]-b[0])<=1e-4:
                xs=round(a[0],4); column=vertical_points.get(xs,[])
                lo=bisect_left(column,min(a[1],b[1])-1e-4); hi=bisect_right(column,max(a[1],b[1])+1e-4)
                candidates=[(xs,y) for y in column[lo:hi]]
            else:
                continue
            # Every segment is continuous. Any endpoint/anchor that lies on it
            # attaches to that segment; an interior crossing stays open unless
            # an endpoint, pin, label, or explicit junction is there.
            for key in candidates[1:]: union(indices[candidates[0]],indices[key])
            connection_operations+=len(candidates)
            if connection_operations>500_000:
                connectivity_limit_hit=True
                break
        # Repeated same-sheet labels name the same net even when separated.
        by_label={}
        for point,meta in anchors:
            if meta[0]=='label':
                name=meta[1]
                if name in by_label: union(indices[point_key(point)],indices[point_key(by_label[name])])
                else: by_label[name]=point
        net_nodes={}; net_names={}
        for point,meta in anchors:
            if meta[0]=='pin':
                root=find(indices[point_key(point)])
                net_nodes.setdefault(root,[]).append(dict(reference=meta[1],pin=meta[2]))
        for point,name,scope_name in labels:
            root=find(indices[point_key(point)])
            net_names.setdefault(root,[]).append(name)
        roots=set(net_nodes)|set(net_names)
        if connectivity_limit_hit:
            # Discard partial topology rather than returning a misleading graph.
            net_nodes={}; net_names={}; roots=set()
        for root in sorted(roots):
            root=find(root); names=sorted(set(net_names.get(root,[])))
            nodes=sorted(net_nodes.get(root,[]),key=lambda n:(n['reference'],n['pin']))
            if nodes or names:
                nets.append(dict(name=' / '.join(names) if names else f'unnamed-{len(nets)+1}',nodes=nodes,
                                 name_source='schematic label' if names else 'geometric connectivity',
                                 power_or_ground=bool(names and re.search(r'(?i)(GND|VCC|VDD|3V3|5V)', ' '.join(names)))))
        present_names={name for net in nets for name in net['name'].split(' / ')}
        for name in sorted(set(unlocated_labels)-present_names):
            nets.append(dict(name=name,nodes=[],name_source='label without coordinates',power_or_ground=bool(re.search(r'(?i)(GND|VCC|VDD|3V3|5V)',name))))
        scope=('KiCad root-sheet orthogonal wire/pin/label connectivity for unmirrored symbols at right-angle rotations. '
               'Pin connectivity is not inferred from pin names alone; '
               'interior crossings without an endpoint, pin, label, or explicit junction are kept separate. Hierarchical sheets, buses, '
               'mirrored symbols and non-right-angle transforms are not resolved. '
               + ('A topology operation limit was exceeded, so this schematic has no derived net graph. ' if connectivity_limit_hit else '')
               + ('Diagonal wires are ignored. ' if unsupported_wire_geometry else '')
               + 'Exported .net is recommended '
               'for authoritative connectivity.')
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
