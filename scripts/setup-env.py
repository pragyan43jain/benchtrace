"""Create local secrets without printing or overwriting them."""
from pathlib import Path
import secrets
p = Path('.env')
if not p.exists():
    p.write_text(f'POSTGRES_PASSWORD={secrets.token_hex(24)}\nENGINE_TOKEN={secrets.token_hex(32)}\nPROVIDER_ENCRYPTION_KEY={secrets.token_hex(32)}\nAPP_ORIGIN=http://localhost:8080\nCOOKIE_SECURE=false\n')
    p.chmod(0o600)
else:
    content = p.read_text()
    lines = content.splitlines()
    found = False
    for index, line in enumerate(lines):
        if line.startswith('PROVIDER_ENCRYPTION_KEY='):
            found = True
            value = line.split('=', 1)[1].strip()
            if not value or value.startswith('replace-with-'):
                lines[index] = f'PROVIDER_ENCRYPTION_KEY={secrets.token_hex(32)}'
    if not found:
        lines.append(f'PROVIDER_ENCRYPTION_KEY={secrets.token_hex(32)}')
    if lines != content.splitlines():
        p.write_text('\n'.join(lines) + '\n')
        p.chmod(0o600)
