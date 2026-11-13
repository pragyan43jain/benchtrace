"""Negative API checks against the configured test deployment."""
import io
import json
import uuid
import zipfile
import urllib.request
import urllib.error
from integration import Client,BASE
c=Client();stamp=uuid.uuid4().hex[:10]
c.request('/auth/register',{'name':'Security test','email':stamp+'@example.test','password':'security-test-passphrase'})
p=c.request('/projects',{'name':"'; DROP TABLE projects; --",'description':'Parameterized SQL probe','platform':'ESP32'},expected=201)['id'];root='/projects/'+p
assert c.request(root)['project']['name']=="'; DROP TABLE projects; --"

def invalid_upload(name,data):
    boundary='probe'+uuid.uuid4().hex
    body=f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}"\r\n\r\n'.encode()+data+f'\r\n--{boundary}--\r\n'.encode()
    request=urllib.request.Request(BASE+'/api'+root+'/files',body,{'Origin':BASE,'Content-Type':'multipart/form-data; boundary='+boundary})
    try:c.http.open(request);raise AssertionError('Unsafe upload accepted')
    except urllib.error.HTTPError as e:assert e.code==400,(e.code,e.read())
invalid_upload('malware.exe',b'not supported')
invalid_upload('fake.pdf',b'not a PDF')
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w') as z:z.writestr('../outside.txt','traversal')
invalid_upload('traversal.zip',buf.getvalue())
buf=io.BytesIO()
with zipfile.ZipFile(buf,'w',zipfile.ZIP_DEFLATED) as z:z.writestr('bomb.txt',b'x'*(10*1024*1024+1))
invalid_upload('oversize.zip',buf.getvalue())
c.request(root+'/compare',{'left':'../file','right':'../file','channel':'sda'},expected=404)
c.request(root+'/search',{'query':''},expected=400)
c.request(root+'/files/not-a-uuid/analyze',{'threshold':0,'baud':0,'cpol':3,'cpha':2},expected=400)
i=c.request(root+'/investigations',{'problem':'Check relationship validation'},expected=201)['id']
c.request(root+'/investigations/'+i+'/tests',{'hypothesis_id':str(uuid.uuid4()),'outcome':'confirms','observation':'This hypothesis does not belong here'},expected=404)
c.request(root+'/investigations/'+i,{'status':'resolved','resolution':''},method='PATCH',expected=400)
config=c.request('/config');assert 'api_key' not in json.dumps(config).lower()
assert Client().request('/config/provider',expected=401)=={'error':'Sign in required'}
assert Client().request('/config/provider-test',{},expected=401)=={'error':'Sign in required'}
assert 'api_key' not in json.dumps(c.request('/config/provider-test',{})).lower()
assert 'api_key' not in json.dumps(c.request('/config/provider')).lower()
c.request('/config/provider',{'model':'x'*201},method='PUT',expected=400)
c.request('/config/provider',{'api_key':'x'*2049},method='PUT',expected=400)
assert c.request(root)['files']==[]
print('PASS: SQL parameter binding, unsupported/forged files, ZIP traversal/expansion limits, path validation, decoder validation, hypothesis ownership, resolution validation, secret-free configuration.')
