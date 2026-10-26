"""Put only this disposable child in the existing desktop session, then drop UID."""
from pathlib import Path
import json
import os

assert os.geteuid() == 0
record = json.loads(Path('/var/lib/samurai/k189-desktop-policy/active-session-cgroup-private.json').read_text())
assert record['User'] == '10000' and record['Active'] == 'yes' and record['Seat'] == 'seat0' and record['Type'] == 'wayland'
leader = Path('/proc') / record['Leader']
assert (leader / 'cgroup').read_text() == record['cgroup']
rows = [line.split(':', 2) for line in record['cgroup'].splitlines()]
assert len(rows) == 1 and rows[0][:2] == ['0', '']
base = Path('/sys/fs/cgroup').resolve(strict=True)
group = (base / rows[0][2].lstrip('/')).resolve(strict=True)
assert group != base and group.is_relative_to(base)
assert (group / 'cgroup.procs').is_file()
# No existing process is moved, and the test leaves the group when it exits.
(group / 'cgroup.procs').write_text(str(os.getpid()))
os.initgroups('cy122', 10000)
os.setgid(10000)
os.setuid(10000)
os.execv('/usr/bin/python3', ['python3', '/usr/share/samurai/ssc/test-active-desktop-client.py'])
