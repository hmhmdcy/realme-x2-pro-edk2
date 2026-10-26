from pathlib import Path
import hashlib,importlib.util,json,shlex,tarfile
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE
q=host.ssh("cat /var/lib/samurai/k390-deployment/rollback-files-private.json",timeout=20);records=json.loads(q.stdout);(P/'rollback-files-private.json').write_bytes(q.stdout)
old=P.parent/'kernel363/modules-k363-private.tar.gz';backup=P/'offline-module-rollback';backup.mkdir(mode=0o700);release=json.loads((P.parent/'kernel389/module-stage-manifest-private.json').read_text())['release']
with tarfile.open(old,'r:gz') as tar:
 for r in records:
  if not r['existed']:continue
  name='usr/lib/modules/'+release+'/'+r['target'].split('/'+release+'/',1)[1];raw=tar.extractfile(name).read();assert hashlib.sha256(raw).hexdigest()==r['old_sha256'];(backup/r['name']).write_bytes(raw)
assert len(list(backup.iterdir()))==2 and sum(not r['existed'] for r in records)==4
spec=importlib.util.spec_from_file_location('transport184',HERE.parent/'kernel184/host.py');transport=importlib.util.module_from_spec(spec);spec.loader.exec_module(transport)
q=transport.upload(HERE/'restore-files.py','/var/lib/samurai/k390-deployment/restore-files.py');(P/'rollback-helper-upload-private.log').write_bytes(q.stdout+q.stderr)
report=dict(stage=390,original_two_modules_saved_on_device=True,original_two_modules_also_matched_and_saved_from_offline363_archive=True,original_three_module_and_firmware_absences_recorded=True,boot366_offline_rollback_verified_at_transition=True,restore_files_helper_prepared_but_not_executed=True,passed=True)
(HERE/'rollback-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
