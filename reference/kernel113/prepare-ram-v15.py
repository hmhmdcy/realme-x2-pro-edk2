from pathlib import Path
import hashlib,json,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
source=out/'c35-reference-private/firmware'
proof=json.loads((ref/'c35-reference-validation.json').read_text())
assert proof['same_linked_base'] and proof['candidate_span_fits_original']
for name,digest in proof['files'].items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
package=out/'c35-slpi-candidate-private.tar'
assert not package.exists()
with tarfile.open(package,'w') as tar:
    for path in sorted(source.iterdir()): tar.add(path,arcname=path.name,recursive=False)
text=(ref/'test-sensor-ram-v13.sh').read_text()
text=text.replace('k113-reboot-audio-clean-9/','k113-reboot-audio-clean-11/')
text=text.replace('ram-v13','ram-v15').replace('RAM_V13','RAM_V15')
text=text.replace('samurai-c28-trial','samurai-c35-trial')
(ref/'test-sensor-ram-v15.sh').write_text(text)
clean=(ref/'quiesce-clean-boot9.sh').read_text().replace('k113-reboot-audio-clean-9/','k113-reboot-audio-clean-10/')
(ref/'quiesce-clean-boot10.sh').write_text(clean)
old=json.loads((ref/'c28-candidate-package.json').read_text())['sha256']
digest=hashlib.sha256(package.read_bytes()).hexdigest()
stager=(ref/'stage-c28-reference.sh').read_text()
assert stager.count(old)==1
stager=stager.replace(old,digest).replace('k113-reboot-audio-clean-8/','k113-reboot-audio-clean-10/')
stager=stager.replace('c28','c35').replace('C28','C35')
(ref/'stage-c35-reference.sh').write_text(stager)
(ref/'c35-candidate-package.json').write_text(json.dumps(dict(sha256=digest,bytes=package.stat().st_size,
    separate_linux_files=True,stock_firmware_overwritten=False,linux_trial_started=False),indent=2)+'\n')
print('C35_SEPARATE_SLPI_CANDIDATE_FOR_BOOT11_PREPARED_OFFLINE')
