import json
import host

code = '''from pathlib import Path
import json
p=Path('/var/lib/samurai/k188-persistent-client/desktop-client-private.txt')
print(p.read_text() if p.exists() else 'NO_DESKTOP_ATTEMPT')
for p in [Path('/usr/share/samurai'),Path('/usr/share/samurai/ssc'),Path('/usr/share/samurai/ssc/test-persistent-client.py')]:
 print(str(p),oct(p.stat().st_mode & 0o777))
'''
p = host.ssh('python3 -', input=code.encode())
(host.PRIVATE / 'client-failure-inspection-private.log').write_bytes(p.stdout + p.stderr)
print(p.stdout.decode())
