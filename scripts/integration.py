"""Run against an isolated/test BenchTrace deployment. Creates uniquely named users/projects."""
import http.cookiejar
import json
import time
import uuid
import urllib.request
import urllib.error
from pathlib import Path
import os
BASE=os.getenv('BENCHTRACE_URL','http://localhost:8080')
class Client:
    def __init__(self):
        self.jar=http.cookiejar.CookieJar();self.http=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))
    def request(self,path,data=None,method=None,expected=200,origin=None):
        body=json.dumps(data).encode() if data is not None else None
        request=urllib.request.Request(BASE+'/api'+path,body,{'Content-Type':'application/json','Origin':origin or BASE},method=method or ('POST' if data is not None else 'GET'))
        try:
            with self.http.open(request,timeout=120) as r:status=r.status;raw=r.read()
        except urllib.error.HTTPError as e:status=e.code;raw=e.read()
        assert status==expected,(path,status,raw[:500])
        if not raw:return None
        try:return json.loads(raw)
        except ValueError:return raw.decode()
    def upload(self,project,path,category=''):
        boundary='benchtrace'+uuid.uuid4().hex
        body=(f'--{boundary}\r\nContent-Disposition: form-data; name="category"\r\n\r\n{category}\r\n--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode()+path.read_bytes()+f'\r\n--{boundary}--\r\n'.encode()
        req=urllib.request.Request(BASE+f'/api/projects/{project}/files',body,{'Origin':BASE,'Content-Type':'multipart/form-data; boundary='+boundary})
        with self.http.open(req,timeout=120) as r:assert r.status==202;return json.load(r)['ids']

def main():
    c=Client();c.request('/health');c.request('/projects',expected=401)
    stamp=uuid.uuid4().hex[:12];creds={'email':f'test-{stamp}@example.test','password':'integration-passphrase-123','name':'Integration Engineer'}
    c.request('/auth/register',creds,origin='https://untrusted.example',expected=403)
    c.request('/auth/register',creds);assert c.request('/auth/me')['email']==creds['email']
    assert list(c.jar) and all('HttpOnly' in x._rest for x in c.jar)
    c.request('/projects',{'name':''},expected=400)
    project=c.request('/projects',{'name':'SIMULATED ESP32 integration '+stamp,'platform':'ESP32','description':'Automated reproducible verification'},expected=201)['id']
    root='/projects/'+project
    c.request(root,{'name':'SIMULATED ESP32 integration '+stamp,'platform':'ESP32','description':'Updated through API'},method='PATCH')
    stranger=Client();stranger.request('/auth/register',{'email':f'other-{stamp}@example.test','password':'integration-passphrase-456','name':'Other Engineer'})
    stranger.request(root,expected=404)
    assert stranger.request('/projects')==[]
    demo=Path(__file__).resolve().parents[1]/'demo'/'esp32-i2c'
    c.request(root+'/preferences',{'threshold':1.65,'baud':9600,'cpol':1,'cpha':1},method='PATCH')
    assert c.request(root)['project']['preferences']['baud']==9600
    c.upload(project,demo/'initial-evidence.zip');c.upload(project,demo/'sensor-symbols.kicad_sch','schematic');c.upload(project,demo/'sensor-datasheet.txt','datasheet')
    c.upload(project,demo/'sensor-model.pdf','datasheet')
    c.upload(project,demo/'verification.csv','measurement')
    deadline=time.monotonic()+180
    while time.monotonic()<deadline:
        files=c.request(root)['files']
        if any(f['status']=='failed' for f in files):raise AssertionError(files)
        if len(files)==9 and all(f['status']=='ready' for f in files):break
        time.sleep(2)
    else:raise AssertionError('Processing timeout')
    wave=next(f for f in files if f['name']=='failure.csv')
    stranger.request(root+'/files/'+wave['id'],expected=404)
    analysis=c.request(root+'/files/'+wave['id'])['analysis'];assert analysis['protocols']['i2c']['frames'][0]['address']==0x49
    assert analysis['protocols']['i2c']['frames'][0]['bytes'][0]['ack'] is False
    components=c.request(root+'/components')
    assert len(components)==5
    symbol=next(x for x in components if x['reference']=='U3')
    assert {k:symbol['properties']['pins'][0][k] for k in ('number','name','electrical_type')}=={'number':'1','name':'SDA','electrical_type':'input'}
    assert symbol['properties']['pins'][0]['sheet_position']==[100.0,80.0]
    sch=next(f for f in files if f['name']=='sensor-symbols.kicad_sch')
    schematic_analysis=c.request(root+'/files/'+sch['id'])['analysis']
    assert any(n['name']=='SDA' and {'reference':'U3','pin':'1'} in n['nodes'] for n in schematic_analysis['nets'])
    assert len(c.request(root+'/history'))>=5
    stranger.request(root+'/components',expected=404)
    comparison=c.request(root+'/compare',{'left':wave['id'],'right':wave['id'],'channel':'sda'})
    assert comparison['rmse_v']==0
    pdf=next(f for f in files if f['name']=='sensor-model.pdf')
    assert c.request(root+'/files/'+pdf['id'])['analysis']['chunks'][0]['page']==1
    search=c.request(root+'/search',{'query':'What is the sensor I2C address?'})
    assert any('0x48' in x['content'] for x in search['evidence'])
    i=c.request(root+'/investigations',{'problem':'SIMULATED ESP32 sensor transaction returns NACK'},expected=201)['id'];ir=root+'/investigations/'+i
    stranger.request(ir,expected=404)
    selected=[f['id'] for f in files if f['name']!='verification.csv']
    c.request(ir+'/diagnose',{'file_ids':[str(uuid.uuid4())]},expected=409)
    result=c.request(ir+'/diagnose',{'file_ids':selected});top=result['hypotheses'][0]
    assert {e['id'] for e in result['evidence']}==set(selected)
    assert top['rule_key']=='address' and top['status']=='unverified'
    assert {e['source'] for e in top['assessment']['supporting_evidence']} >= {'firmware.ino','sensor-datasheet.txt','failure.csv'}
    c.request(ir+'/tests',{'hypothesis_id':top['id'],'observation':'SIMULATED: 0x48 ACKs, while 0x49 NACKs in the disclosed generator. No physical verification.','outcome':'confirms'},expected=201)
    result=c.request(ir+'/diagnose',{'file_ids':selected});assert next(h for h in result['hypotheses'] if h['id']==top['id'])['status']=='confirmed'
    c.request(ir,{'status':'resolved','resolution':'SIMULATED correction: change address to 0x48. Physical validation remains unperformed.'},method='PATCH')
    report=c.request(ir+'/report');assert 'user-confirmed' in report and '0x48' in report and 'SIMULATED' in report
    c.request(ir+'/save',{},expected=201);assert any(k['investigation_id']==i for k in c.request('/knowledge?q=sensor'))
    assert any(k['verification']=='user_confirmed' for k in c.request('/knowledge?verified=true'))
    procedure=c.request(root+'/knowledge',{'title':'Verify sensor address','content':'Read the exact part datasheet, inspect straps, capture the bus, and compare ACK responses.'},expected=201)
    assert any(k['id']==procedure['id'] for k in c.request('/knowledge?q=address'))
    assert not any(k['id']==procedure['id'] for k in c.request('/knowledge?verified=true'))
    assert stranger.request('/knowledge')==[]
    c.request('/auth/me',{'name':'Updated Engineer','current_password':creds['password'],'new_password':'updated-test-passphrase'},method='PATCH')
    creds['password']='updated-test-passphrase'
    assert c.request('/auth/me')['name']=='Updated Engineer'
    c.request('/auth/logout',{});c.request('/auth/me',expected=401)
    c.request('/auth/login',{'email':creds['email'],'password':'wrong-password'},expected=401)
    c.request('/auth/login',{'email':creds['email'],'password':creds['password']});assert c.request(ir)['investigation']['status']=='resolved'
    print('PASS: auth, CSRF, project management, owner isolation, ZIP upload, background processing, waveform, retrieval, diagnosis, test persistence, report, knowledge, logout/login.')
if __name__=='__main__':main()
