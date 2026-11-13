"""Bounded sampled-signal analysis. Times are seconds; amplitudes are volts."""
import io
import csv
import numpy as np
import pandas as pd
from scipy.signal import find_peaks


def parse_csv(text):
    headers=next(csv.reader(io.StringIO(text)),[])
    if len(headers)!=len(set(h.lower() for h in headers)):
        raise ValueError('Duplicate channel names')
    frame = pd.read_csv(io.StringIO(text))
    if 'time' not in frame or not 3 <= len(frame) <= 200_000 or not 2 <= len(frame.columns) <= 17:
        raise ValueError('CSV requires time and 1–16 channels, 3–200000 samples')
    if len(set(frame.columns)) != len(frame.columns):
        raise ValueError('Duplicate channel names')
    frame = frame.apply(pd.to_numeric, errors='raise')
    if not np.isfinite(frame.to_numpy()).all() or np.max(np.abs(frame.to_numpy()))>1e12:
        raise ValueError('Samples must be finite')
    t = frame.pop('time').to_numpy()
    if np.any(np.diff(t) < 1e-15):
        raise ValueError('Time must be strictly increasing in seconds')
    return t, {str(k).lower(): v.to_numpy() for k, v in frame.items()}


def stats(t, y):
    dt = np.diff(t)
    uniform = bool(np.max(abs(dt - np.median(dt))) <= np.median(dt) * .01)
    filtered = np.convolve(y, np.ones(5)/5, mode='valid') if len(y) >= 5 else y
    prominence=max(float(np.ptp(y))*.1, 1e-12)
    peaks, _ = find_peaks(y, prominence=prominence)
    troughs, _ = find_peaks(-y, prominence=prominence)
    result = dict(min=float(min(y)), max=float(max(y)), mean=float(np.mean(y)), rms=float(np.sqrt(np.mean(y*y))),
                  sample_rate_hz=float(1/np.median(dt)), sampling_uniform=uniform,
                  sampling_jitter_fraction=float(np.std(dt)/np.mean(dt)), peak_count=len(peaks),
                  trough_count=len(troughs), extrema_method='Prominence-based local maxima and minima; threshold is 10% of capture peak-to-peak span',
                  noise_estimate_v=float(np.median(abs(np.diff(y)-np.median(np.diff(y))))/.67448975/np.sqrt(2)),
                  noise_method='Robust first-difference estimate; edges and correlated noise can bias it',
                  moving_average=filtered[::max(1,len(filtered)//1000)].tolist(),
                  moving_average_time=(t[2:-2] if len(y)>=5 else t)[::max(1,len(filtered)//1000)].tolist(),
                  moving_average_method='Five-sample centered mean; display filtering does not alter decoder inputs')
    if uniform:
        amplitudes = np.abs(np.fft.rfft((y-np.mean(y))*np.hanning(len(y)))) * 2/max(np.sum(np.hanning(len(y))),1)
        frequencies = np.fft.rfftfreq(len(y), float(np.median(dt)))
        indices = np.argsort(amplitudes[1:])[-20:]+1
        result['spectrum'] = [dict(hz=float(frequencies[i]), amplitude=float(amplitudes[i])) for i in indices[::-1]]
        result['dominant_frequency_hz'] = float(frequencies[np.argmax(amplitudes[1:])+1]) if np.ptp(y)>0 else None
    else:
        result['warning'] = 'FFT withheld: sampling intervals vary by more than 1%'
    return result


def digital(y, threshold):
    return np.asarray(y) >= threshold


def decode_i2c(t, scl, sda, threshold=1.65):
    c, d = digital(scl,threshold), digital(sda,threshold)
    transitions = np.flatnonzero(c[1:] != c[:-1])+1
    warnings = []
    if len(transitions)>1 and min(np.diff(t[transitions])) < 3*max(np.diff(t)):
        return dict(frames=[], reliable=False, warnings=['Insufficient samples: require at least 3 samples per SCL half-period'])
    if np.any((~c[:-1] & c[1:]) & (d[1:] != d[:-1])):
        warnings.append('Simultaneous SCL/SDA transitions: edge ordering is ambiguous at this sample rate')
    frames, bits, current = [], [], None
    for i in range(1,len(t)):
        start = c[i-1] and c[i] and d[i-1] and not d[i]
        stop = c[i-1] and c[i] and not d[i-1] and d[i]
        if start or stop:
            if current is not None:
                current['end'] = float(t[i]); current['termination'] = 'restart' if start else 'stop'
                if len(bits)>1: warnings.append('Incomplete byte at transaction boundary')
                frames.append(current)
            current = dict(start=float(t[i]), bytes=[]) if start else None
            bits = []
        elif current is not None and not c[i-1] and c[i]:
            bits.append(int(d[i]))
            if len(bits)==9:
                value = sum(b << (7-j) for j,b in enumerate(bits[:8]))
                current['bytes'].append(dict(value=value, ack=not bool(bits[8]), time=float(t[i])))
                if len(current['bytes'])==1:
                    current.update(address=value>>1, direction='read' if value&1 else 'write')
                    if value&0xF8==0xF0:warnings.append('10-bit address prefix detected; this decoder supports only 7-bit addresses')
                bits=[]
    if current is not None:
        current['termination']='truncated'; frames.append(current); warnings.append('Capture ended without STOP')
    if not frames: warnings.append('No complete START-address transaction found')
    if any(not f.get('bytes') for f in frames): warnings.append('Transaction has no complete address byte')
    periods = np.diff(t[np.flatnonzero(~c[:-1] & c[1:])+1])
    return dict(frames=frames, reliable=not warnings, warnings=list(dict.fromkeys(warnings)),
                clock_hz=float(1/np.median(periods)) if len(periods) else None,
                limitations='7-bit addressing only; digital threshold does not establish rise-time compliance or pull-up resistance')


def decode_uart(t, rx, baud=115200, threshold=1.65):
    if not 1 <= baud <= 10_000_000: raise ValueError('Invalid baud rate')
    if max(np.diff(t))*baud > .125*(1+1e-9):
        return dict(frames=[],reliable=False,warnings=['Require at least 8 samples per UART bit'])
    d=digital(rx,threshold); frames=[]; until=-1
    warnings=[] if d[0] else ['Capture starts with UART RX low; initial frame boundary is unknown']
    for i in np.flatnonzero(d[:-1] & ~d[1:])+1:
        if t[i] < until: continue
        times=t[i]+np.arange(.5,10,1)/baud
        if times[-1]>t[-1]: return dict(frames=frames,reliable=False,warnings=['Truncated UART frame'])
        indices=np.searchsorted(t,times); bits=d[indices]
        if bits[0]: continue
        frames.append(dict(time=float(t[i]),value=sum(int(b)<<j for j,b in enumerate(bits[1:9])),framing_error=not bool(bits[9])))
        until=t[i]+9.5/baud
    return dict(frames=frames,reliable=bool(frames) and not warnings and not any(f['framing_error'] for f in frames),warnings=warnings+([] if frames else ['No complete UART frames found']),format='8N1, non-inverted')


def decode_spi(t, clk, mosi, cs, cpol=0, cpha=0, threshold=1.65):
    if cpol not in (0,1) or cpha not in (0,1): raise ValueError('CPOL/CPHA must be 0 or 1')
    c,d,s=digital(clk,threshold),digital(mosi,threshold),digital(cs,threshold)
    edges=np.flatnonzero(c[1:]!=c[:-1])+1
    if len(edges)>1 and min(np.diff(t[edges])) < 3*max(np.diff(t)):
        return dict(frames=[],reliable=False,warnings=['Require 3 samples per SPI half-period'])
    frames=[];bits=[];warnings=[]
    boundary_known=bool(s[0])
    if not boundary_known: warnings.append('Capture starts with CS active; initial word boundary is unknown')
    boundary_known=True
    for i in range(1,len(t)):
        if s[i]:
            boundary_known=True
            if bits: warnings.append('Partial SPI word at chip-select boundary');bits=[]
            continue
        if s[i]!=s[i-1] and c[i]!=c[i-1]: warnings.append('Simultaneous chip-select and clock transition; ordering is ambiguous')
        if c[i]!=c[i-1] and ((c[i]!=bool(cpol)) != bool(cpha)):
            bits.append(int(d[i]))
            if len(bits)==8:
                frames.append(dict(time=float(t[i]),value=sum(b<<(7-j) for j,b in enumerate(bits))));bits=[]
    if bits: warnings.append('Truncated SPI word')
    if not frames:warnings.append('No complete SPI words found')
    return dict(frames=frames,reliable=not warnings,warnings=warnings,format='8-bit MSB first, active-low CS, MOSI only')


def analyze_csv(text, options=None):
    options=options or {};t,channels=parse_csv(text);threshold=options.get('threshold',1.65)
    result=dict(kind='waveform',sample_count=len(t),duration=float(t[-1]-t[0]),channels={},protocols={})
    # Preserve transitions in the displayed data; cap response size explicitly.
    indices=np.arange(len(t)) if len(t)<=10000 else np.unique(np.concatenate([np.linspace(0,len(t)-1,2000,dtype=int)]+[np.concatenate((np.flatnonzero(np.diff(digital(y,threshold))),np.flatnonzero(np.diff(digital(y,threshold)))+1)) for y in channels.values()]))
    if len(indices)>20000: indices=indices[np.linspace(0,len(indices)-1,20000,dtype=int)]
    result['preview_truncated']=len(indices)<len(t)
    result['time']=t[indices].tolist()
    for name,y in channels.items():
        result['channels'][name]=dict(samples=y[indices].tolist(),statistics=stats(t,y),threshold_crossings=int(np.count_nonzero(np.diff(digital(y,threshold)))))
    if {'scl','sda'} <= channels.keys(): result['protocols']['i2c']=decode_i2c(t,channels['scl'],channels['sda'],threshold)
    if 'rx' in channels: result['protocols']['uart']=decode_uart(t,channels['rx'],options.get('baud',115200),threshold)
    if {'clk','mosi','cs'} <= channels.keys(): result['protocols']['spi']=decode_spi(t,channels['clk'],channels['mosi'],channels['cs'],options.get('cpol',0),options.get('cpha',0),threshold)
    return result


def compare_csv(left,right,channel):
    lt,lc=parse_csv(left);rt,rc=parse_csv(right)
    if channel not in lc or channel not in rc:raise ValueError('Channel missing')
    start=max(lt[0],rt[0]);end=min(lt[-1],rt[-1]);mask=(lt>=start)&(lt<=end)
    if mask.sum()<3:raise ValueError('Insufficient overlapping time range')
    x=lc[channel][mask];y=np.interp(lt[mask],rt,rc[channel]);delta=x-y
    return dict(channel=channel,samples=int(mask.sum()),start=float(start),end=float(end),rmse_v=float(np.sqrt(np.mean(delta**2))),max_difference_v=float(np.max(abs(delta))),mean_difference_v=float(np.mean(delta)),method='Absolute timestamp alignment; right capture linearly interpolated to left. No inferred trigger alignment.')
