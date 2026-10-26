from pathlib import Path
import host, sys
path = Path(sys.argv[1])
p = host.ssh('python3 -', input=path.read_bytes(), timeout=int(sys.argv[2]) if len(sys.argv) > 2 else 90)
(host.PRIVATE / (path.stem + '-host-private.log')).write_bytes(p.stdout + p.stderr)
print(p.stdout.decode()[-6500:])
