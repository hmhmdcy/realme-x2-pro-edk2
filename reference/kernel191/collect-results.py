from pathlib import Path
import hashlib,json,subprocess,tarfile
import host
ref=Path(__file__).resolve().parent
try:p=host.ssh('python3 -',input=(ref/'final-and-export.py').read_bytes(),timeout=180)
except subprocess.CalledProcessError as e:
 (host.PRIVATE/'final-export-failed-private.log').write_bytes(e.stdout+e.stderr);raise SystemExit('Final capture/export failed; private log retained')
record=json.loads(p.stdout);archive=host.PRIVATE/'evidence-private.tar.gz'
host.download('/var/lib/samurai/k191-final/evidence-private.tar.gz',archive);assert hashlib.sha256(archive.read_bytes()).hexdigest()==record['archive_sha256']
with tarfile.open(archive) as tar:
 manifest=json.load(tar.extractfile('manifest-private.json'))
 for name,digest in manifest.items():assert hashlib.sha256(tar.extractfile(name).read()).hexdigest()==digest
 outputs={
 'baseline-validation.json':'k191-baseline/summary.json',
 'mm-deployment-validation.json':'k191-mm-deploy/summary.json',
 'assistance-injection-validation.json':'k191-assistance/summary.json',
 'utc-injection-validation.json':'k191-utc-injection/summary.json',
 'mm-location-stream-validation.json':'k191-mm-stream/summary.json',
 'sv-observer-validation.json':'k191-sv-observer-r3/summary.json'}
 for target,source in outputs.items():
  report=json.load(tar.extractfile(source));(ref/target).write_text(json.dumps(report,indent=2)+'\n')
 (host.PRIVATE/'ModemManager.before191').write_bytes(tar.extractfile('k191-mm-deploy/ModemManager.original').read())
 (host.PRIVATE/'ModemManager.patched191').write_bytes(tar.extractfile('k191-mm-build/candidate/ModemManager').read())
(ref/'final-validation.json').write_text(json.dumps(record.pop('final'),indent=2)+'\n')
record.update(host_archive_sha256_verified=True,all_member_hashes_verified=True,original_and_candidate_binaries_saved=True,raw_location_modem_and_identity_data_private=True)
(ref/'evidence-export-validation.json').write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
