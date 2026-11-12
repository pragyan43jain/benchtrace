"""Run untrusted document parsing in a disposable, bounded child process."""
import json
import os
import subprocess
import sys
import tempfile

MAX_RESULT=48*1024*1024

def isolated_process(path,options):
    # Do not give parser children service/provider credentials or shell access.
    env={k:v for k,v in os.environ.items() if k in ('PATH','PYTHONPATH','MODEL_CACHE','HF_HUB_OFFLINE','EMBEDDING_MODE')}
    env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',HOME='/tmp')
    with tempfile.TemporaryFile() as output,tempfile.TemporaryFile() as errors:
        try:
            completed=subprocess.run([sys.executable,'-m','app.process_worker',str(path),json.dumps(options)],env=env,stdout=output,stderr=errors,timeout=65,check=False)
        except subprocess.TimeoutExpired as exc:
            raise ValueError('Processing exceeded the 65-second per-file limit') from exc
        if completed.returncode!=0:raise ValueError('Parser failed or exceeded its resource limit; inspect file format and size')
        output.seek(0);data=output.read(MAX_RESULT+1)
        if len(data)>MAX_RESULT:raise ValueError('Analysis result exceeds 48 MiB')
        try:result=json.loads(data)
        except ValueError as exc:raise ValueError('Parser did not produce a valid analysis') from exc
        if 'processing_error' in result:raise ValueError(result['processing_error'])
        return result
