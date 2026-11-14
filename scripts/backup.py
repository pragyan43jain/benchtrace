#!/usr/bin/env python3
"""Consistent local Compose backup. Briefly stops application writers."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.chdir(Path(__file__).resolve().parents[1])
os.umask(0o077)
target = Path(sys.argv[1] if len(sys.argv)>1 else '.data/backups/'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
target.mkdir(parents=True, exist_ok=False)
def run(*args, **kwargs):
    return subprocess.run(['docker','compose',*args], check=True, **kwargs)
active = run('ps','--services','--status','running',capture_output=True,text=True).stdout.split()
writers = [s for s in ('web','api','engine') if s in active]
try:
    if writers: run('stop',*writers)
    with (target/'database.dump').open('wb') as out:
        run('exec','-T','db','pg_dump','-U','benchtrace','-d','benchtrace','-Fc',stdout=out)
    with (target/'uploads.tar.gz').open('wb') as out:
        run('run','--rm','--no-deps','--entrypoint','tar','engine','-czf','-','-C','/uploads','.',stdout=out)
    manifest = {'format':1,'source_revision':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in target.iterdir()}}
    (target/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
finally:
    if writers: run('start',*reversed(writers))
print('Backup:',target.resolve())
print('Keep the original .env/provider encryption key separately; it is not included.')
