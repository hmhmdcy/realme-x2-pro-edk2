"""Continue the prepared trial only after native startup checks completed."""
from pathlib import Path
import hashlib,json
import host

ref=Path(__file__).resolve().parent
path=ref/'test-a11-userspace-trial.sh'
host.ssh('test -f /var/lib/samurai/k187-reboot-runtime/summary.json && test ! -e /var/lib/samurai/k187-a11-userspace')
host.ssh('sha256sum -c -',input=(hashlib.sha256(path.read_bytes()).hexdigest()+'  /var/lib/samurai/k187-tools/'+path.name+'\n').encode())
p=host.ssh('nohup sh /var/lib/samurai/k187-tools/test-a11-userspace-trial.sh > /var/lib/samurai/k187-a11-userspace-worker-private.log 2>&1 < /dev/null & echo $!')
(host.PRIVATE/'userspace-worker-pid-private.txt').write_bytes(p.stdout)
print(json.dumps({'native_startup_gate_passed':True,'prepared_trial_started_once':True,
    'no_reboot_or_flash_requested':True}))
