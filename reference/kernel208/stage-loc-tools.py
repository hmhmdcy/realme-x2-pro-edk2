from pathlib import Path
import host

here=Path(__file__).resolve().parent
native="from pathlib import Path; import os; os.umask(0o077); root=Path('/var/lib/samurai'); assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes(); (root/'k208-loc-tools').mkdir(mode=0o700)"
host.ssh('python3 -',input=native.encode())
host.upload(here/'loc_nmea.py','/var/lib/samurai/k208-loc-tools/loc_nmea.py')
print('Private LOC diagnostic module staged; no GNSS session or settings change.')
