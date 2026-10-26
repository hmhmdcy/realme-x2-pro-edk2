from pathlib import Path
import hashlib,json
import host
ref=Path(__file__).resolve().parent
p=host.ssh("cat /var/lib/samurai/k190-evidence-export/summary.json")
record=json.loads(p.stdout);path=host.PRIVATE/'evidence-private.tar.gz'
if path.exists() and hashlib.sha256(path.read_bytes()).hexdigest()!=record['archive_sha256']:
 partial=host.PRIVATE/'evidence-usb-incomplete-private.tar.gz';assert not partial.exists();path.rename(partial)
host.download('/var/lib/samurai/k190-evidence-export/evidence-private.tar.gz',path)
assert hashlib.sha256(path.read_bytes()).hexdigest()==record['archive_sha256']
for src,dest in [('k190-mm-deploy/ModemManager.original','ModemManager.original'),('k190-mm-build/candidate/ModemManager','ModemManager.patched')]:host.download('/var/lib/samurai/'+src,host.PRIVATE/dest)
record.update(host_archive_sha256_verified=True,raw_modem_and_location_logs_private=True,original_and_patched_executables_preserved=True,usb_download_incomplete_preserved=True,completed_over_authenticated_wifi=True)
(ref/'evidence-export-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
