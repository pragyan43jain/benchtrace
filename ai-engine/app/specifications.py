"""Extract explicit statements, preserving their source and applicability limits.

This is intentionally a bounded grammar, not a datasheet table interpretation
model. It never treats an absolute maximum as a recommended operating value.
"""
import re

NUMBER=r'[-+]?\d+(?:\.\d+)?'
UNITS=r'(?:mV|V|mA|A|MHz|kHz|Hz|ns|µs|us|ms|s|pF|nF|µF|uF|kΩ|Ω|ohms?)'
RANGE=re.compile(rf'(?P<low>{NUMBER})\s*(?:to|–|—|\.\.|-)\s*(?P<high>{NUMBER})\s*(?P<unit>{UNITS})\b',re.I)
QUANTITY=re.compile(rf'(?P<value>{NUMBER})\s*(?P<unit>{UNITS})\b',re.I)

def characteristics(text,page):
    result=[]
    for raw in text.splitlines():
        line=raw.strip()
        if not line or len(line)>1000:continue
        lower=line.lower()
        protocols=[p for p in ('I2C','SPI','UART') if re.search(r'\b'+p+r'\b',line,re.I)]
        base={'page':page,'excerpt':line,'classification':'documented statement; applicability and extraction require review'}
        if protocols:result.append({**base,'kind':'protocol','protocols':protocols})
        pin=re.match(r'^(?:Pin\s+)?(?P<number>\d{1,3})\s*[:|,\s]\s*(?P<name>[A-Z][A-Z0-9_/+-]{1,15})\s*[:|,\s]\s*(?P<description>.+)$',line)
        if pin:result.append({**base,'kind':'pin',**pin.groupdict()})
        kind=None
        if re.search(r'\b(voltage|vdd|vcc|supply|logic level)\b',lower):kind='voltage'
        elif re.search(r'\b(clock|frequency|baud|rise time|fall time|setup|hold time|timing|pulse)\b',lower):kind='timing'
        elif re.search(r'\b(current|capacitance|resistance|pull.up)\b',lower):kind='electrical'
        if kind:
            condition='absolute_maximum' if 'absolute max' in lower else 'recommended_operating' if re.search(r'recommended|operating',lower) else 'unspecified'
            match=RANGE.search(line)
            if match:
                low,high=float(match['low']),float(match['high'])
                if low<=high:result.append({**base,'kind':kind,'minimum':low,'maximum':high,'unit':match['unit'],'condition':condition})
            else:
                for match in QUANTITY.finditer(line):
                    result.append({**base,'kind':kind,'value':float(match['value']),'unit':match['unit'],'condition':condition,'bound':'maximum' if re.search(r'\bmax(?:imum)?\b',lower) else 'minimum' if re.search(r'\bmin(?:imum)?\b',lower) else 'unspecified'})
    return result
