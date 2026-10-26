from pathlib import Path
import hashlib
import json
import os
import subprocess

out = Path('/var/lib/samurai/k142-console-latency-after-ab')
boot = Path('/var/lib/samurai/k142-first-runtime/boot-id-private.txt').read_bytes()
assert os.geteuid() == 0 and Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
assert os.uname().version.startswith('#140 ') and not out.exists()
ab = json.loads(Path('/var/lib/samurai/k142-console-latency-ab/ab-validation.json').read_text())
assert ab['error'] is None and ab['original_ignore_loglevel_restored'] and ab['affinity_restored']
paths = [p.joinpath('tx_journal') for p in Path('/sys/bus/platform/drivers/qcom_eud_com').iterdir()
    if p.name != 'module' and p.joinpath('tx_journal').is_file()]
assert len(paths) == 1
out.mkdir(mode=0o700)
out.joinpath('boot-id-private.txt').write_bytes(boot)
out.joinpath('tx-journal-private.bin').write_bytes(paths[0].read_bytes())
out.joinpath('ignore-loglevel.txt').write_text(Path('/sys/module/printk/parameters/ignore_loglevel').read_text())
with out.joinpath('desktop-pids-private.txt').open('w') as file:
    for name in ['phosh','phoc']:
        subprocess.run(['pgrep','-x',name],stdout=file,stderr=subprocess.STDOUT,check=True)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot
out.joinpath('SHA256SUMS').write_text(''.join(hashlib.sha256(p.read_bytes()).hexdigest()+'  ./'+p.name+'\n'
    for p in sorted(out.iterdir()) if p.is_file()))
subprocess.run(['tar','-C',str(out),'-czf','/tmp/k142-console-latency-after-ab-private.tar.gz','.'],check=True,timeout=20)
print('K142_POST_AB_JOURNAL_AND_DESKTOP_READ_ONLY_CAPTURED')
