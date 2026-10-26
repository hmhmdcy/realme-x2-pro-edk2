from pathlib import Path
import dbus,json,os,sys
sys.path.insert(0,'/var/lib/samurai/k208-loc-tools')
from loc_nmea import LocSession
os.umask(0o077)
root=Path('/var/lib/samurai')
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k208-baseline/boot-id-private.txt').read_bytes()
out=root/'k208-nmea-mask';out.mkdir(mode=0o700)
session=LocSession();report=dict(stage=208,read_only=True,engine_start_sent=False)
try:
    session.open()
    report['nmea_mask']=session.nmea_mask()
finally:
    report.update(session.close());report['receipts']=session.receipts
    (out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
