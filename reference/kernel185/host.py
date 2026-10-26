"""Reuse the authenticated USB transport with a separate private evidence folder."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location('transport184', Path(__file__).resolve().parent.parent / 'kernel184/host.py')
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel185')
PRIVATE.mkdir(exist_ok=True)
ssh = transport.ssh
upload = transport.upload
download = transport.download
SSH = transport.SSH
OPTIONS = transport.OPTIONS

if __name__ == '__main__':
    import subprocess
    import sys
    path = Path(sys.argv[1])
    try:
        p = ssh('python3 -', input=path.read_bytes(), timeout=55)
    except subprocess.CalledProcessError as e:
        (PRIVATE / (path.stem + '-failed-private.log')).write_bytes(e.stdout + e.stderr)
        print(e.stderr.decode(errors='replace'))
        raise SystemExit(e.returncode)
    (PRIVATE / (path.stem + '-host-private.log')).write_bytes(p.stdout + p.stderr)
    print(p.stdout.decode().strip())
