"""Build-time model fetch with immutable revision and per-file integrity checks."""
import hashlib
import json
import urllib.request
from pathlib import Path

lock = json.loads(Path('model.lock.json').read_text())
root = Path('/models') / lock['revision']
root.mkdir(parents=True, exist_ok=True)
for name, expected in lock['files'].items():
    url = f"https://huggingface.co/{lock['repository']}/resolve/{lock['revision']}/{name}"
    digest = hashlib.sha256()
    with urllib.request.urlopen(url, timeout=90) as response, (root / name).open('wb') as target:
        while block := response.read(1024 * 1024):
            target.write(block)
            digest.update(block)
    if digest.hexdigest() != expected:
        raise RuntimeError(f'Model integrity check failed: {name}')
    print('Verified ' + name, flush=True)
Path('/models/model-path').write_text(str(root))
print('Verified embedding model revision ' + lock['revision'])
