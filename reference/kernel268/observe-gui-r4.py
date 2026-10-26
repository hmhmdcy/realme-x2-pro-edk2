"""Read the completed r4 context without re-running it."""
import host
code="from pathlib import Path;print(Path('/var/lib/samurai/k268-snapshot-gui-r4/failure-private.txt').read_text())"
q=host.ssh('python3 -',input=code.encode(),timeout=20)
print(q.stdout.decode())
