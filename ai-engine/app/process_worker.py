"""Internal parser entry point. Never import or execute uploaded source files."""
import json
import resource
import sys

# The parent enforces wall time; these apply to the isolated parser only.
resource.setrlimit(resource.RLIMIT_CPU,(60,60))
resource.setrlimit(resource.RLIMIT_AS,(2*1024**3,2*1024**3))
resource.setrlimit(resource.RLIMIT_FSIZE,(64*1024**2,64*1024**2))
resource.setrlimit(resource.RLIMIT_NOFILE,(128,128))
from .evidence import process
try:
    result=process(sys.argv[1],json.loads(sys.argv[2]))
except Exception as exc:
    result={'processing_error':f'{type(exc).__name__}: {str(exc)[:300]}'}
json.dump(result,sys.stdout,allow_nan=False)
