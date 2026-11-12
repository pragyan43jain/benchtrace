"""Create local secrets without printing or overwriting them."""
from pathlib import Path
import secrets
p = Path('.env')
if not p.exists():
    p.write_text(f'POSTGRES_PASSWORD={secrets.token_hex(24)}\nENGINE_TOKEN={secrets.token_hex(32)}\nAPP_ORIGIN=http://localhost:8080\nCOOKIE_SECURE=false\n')
    p.chmod(0o600)
