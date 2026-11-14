#!/usr/bin/env python3
"""Restore to a NEW isolated Compose project; never overwrite existing volumes."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tarfile

os.chdir(Path(__file__).resolve().parents[1])
if len(sys.argv)!=4:
    raise SystemExit('Usage: python3 scripts/restore.py BACKUP NEW_PROJECT UNUSED_PORT')
source, project, port = Path(sys.argv[1]),sys.argv[2],int(sys.argv[3])
if not re.fullmatch(r'benchtrace-restore-[a-z0-9-]+',project) or not 1024<=port<=65535:
    raise SystemExit('Use a project named benchtrace-restore-<name> and port 1024..65535')
manifest=json.loads((source/'manifest.json').read_text())
if manifest.get('format')!=1 or set(manifest['files'])!={'database.dump','uploads.tar.gz'}:
    raise SystemExit('Unsupported backup manifest')
for name,digest in manifest['files'].items():
    if hashlib.sha256((source/name).read_bytes()).hexdigest()!=digest:
        raise SystemExit('Backup checksum mismatch: '+name)
with tarfile.open(source/'uploads.tar.gz') as archive:
    for member in archive:
        path=Path(member.name)
        if path.is_absolute() or '..' in path.parts or not (member.isfile() or member.isdir()):
            raise SystemExit('Unsafe upload archive member')
for kind in ('volume','container'):
    command=['docker',kind,'ls',*(['-a'] if kind=='container' else []),'-q','--filter','label=com.docker.compose.project='+project]
    if subprocess.check_output(command).strip():
        raise SystemExit('Refusing to overwrite existing project resources')
# The existing .env provides the separately protected encryption key.
env=dict(os.environ,BENCHTRACE_PORT=str(port),APP_ORIGIN='http://localhost:'+str(port))
def run(*args,**kwargs):
    return subprocess.run(['docker','compose','-p',project,*args],env=env,check=True,**kwargs)
run('build')
run('up','-d','--wait','db','redis')
with (source/'database.dump').open('rb') as data:
    run('exec','-T','db','pg_restore','-U','benchtrace','-d','benchtrace','--no-owner','--exit-on-error',stdin=data)
# Create the upload volume, then restore through a temporary root helper.
run('create','api')
container=run('ps','-aq','api',capture_output=True,text=True).stdout.strip()
info=json.loads(subprocess.check_output(['docker','inspect',container]))[0]
volume=next(m['Name'] for m in info['Mounts'] if m['Destination']=='/uploads')
with (source/'uploads.tar.gz').open('rb') as data:
    subprocess.run(['docker','run','--rm','-i','--user','0','--entrypoint','tar','-v',volume+':/restore',info['Image'],'-xzf','-','-C','/restore'],stdin=data,check=True)
run('up','-d','--wait')
print('Restored isolated deployment: http://localhost:'+str(port))
print('Keep using the same port and APP_ORIGIN when restarting this project.')
