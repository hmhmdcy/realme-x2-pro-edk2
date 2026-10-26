from pathlib import Path
import host
here=Path(__file__).resolve().parent
host.ssh('test ! -e /var/lib/samurai/k205-diagnostic-cycles');host.upload(here/'test-diagnostic-cycles.py','/var/lib/samurai/k205-tools/test-diagnostic-cycles.py')
p=host.ssh('nohup python3 /var/lib/samurai/k205-tools/test-diagnostic-cycles.py > /var/lib/samurai/k205-diagnostic-worker-private.log 2>&1 < /dev/null & echo $!');(host.PRIVATE/'diagnostic-worker-pid-private.txt').write_bytes(p.stdout);print('Started at most eight initialization cycles, stopping early after a captured baud error; poll this PID.')
