"""Stop the confirmed live make once for a measured resource adjustment."""
from pathlib import Path
import json,os,signal,subprocess
import host
P=host.PRIVATE;marker=P/'parallelism-adjustment-private.json';assert not marker.exists()
state=json.loads((P/'boot-build-state-private.json').read_text());assert not state['terminal'] and state['phase']=='image-modules'
child=Path('/proc',str(state['child_pid']));cmd=(child/'cmdline').read_bytes();assert b'/mnt/samurai-full282/source354' in cmd and b'-j3' in cmd
memory={line.split(':',1)[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if len(line.split())>=2}
assert os.cpu_count()>=8 and memory['MemAvailable']>4*1024*1024
record=dict(reason='Measured 12 CPUs and more than4GiB available; increase parallelism from3 to8',child_pid=state['child_pid'],worker=state['worker'],signal='SIGINT',request_count=1)
marker.write_text(json.dumps(record,indent=2)+'\n');os.kill(state['child_pid'],signal.SIGINT)
print('Sent one intentional SIGINT to confirmed make; observe the existing handle before resuming.')
