from pathlib import Path
import hashlib,json,re,tarfile

ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel113')
out=Path('/mnt/e/edk2-samurai-out/kernel113')
source=out/'a11-reference-private/firmware'
proof=json.loads((ref/'a11-reference-validation.json').read_text())
assert proof['same_linked_base'] and proof['candidate_span_fits_original']
assert proof['split_file_sizes_match_mdt'] and not proof['identical_to_original_slpi']
for name,digest in proof['files'].items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
assert set(p.name for p in source.iterdir())==set(proof['files'])|{'SHA256SUMS'}
differences={}
for version in ('c28','c35'):
    other=json.loads((ref/(version+'-reference-validation.json')).read_text())['files']
    differences[version]=sum(other.get(name)!=digest for name,digest in proof['files'].items())
assert all(differences.values()),'identical firmware needs no duplicate runtime trial'

text=(ref/'test-sensor-ram-v16.sh').read_text()
assert 'k113-reboot-audio-clean-12/' in text and 'samurai-c35-trial' in text
text=text.replace('ram-v16','ram-v18').replace('RAM_V16','RAM_V18')
text=text.replace('k113-reboot-audio-clean-12/','k113-reboot-audio-clean-14/')
text=text.replace('samurai-c35-trial','samurai-a11-trial')
assert 'for kind in light magnetometer gyroscope compass; do' in text
package=out/'a11-slpi-candidate-private.tar'
assert not package.exists()
with tarfile.open(package,'w') as archive:
    for path in sorted(source.iterdir()):
        assert path.is_file() and not path.is_symlink()
        info=archive.gettarinfo(str(path),arcname=path.name)
        info.uid=info.gid=0; info.uname=info.gname='root'; info.mode=0o440
        with path.open('rb') as file: archive.addfile(info,file)
digest=hashlib.sha256(package.read_bytes()).hexdigest()
stager=(ref/'stage-c35-reference.sh').read_text()
assert 'k113-reboot-audio-clean-10/' in stager
stager=stager.replace('k113-reboot-audio-clean-10/','k113-reboot-audio-clean-13/')
stager,count=re.subn(r"echo '[0-9a-f]{64}  /tmp/k113-c35", "echo '"+digest+'  /tmp/k113-c35',stager)
assert count==1
stager=stager.replace('c35','a11').replace('C35','A11')
(ref/'test-sensor-ram-v18.sh').write_text(text)
(ref/'stage-a11-reference.sh').write_text(stager)
report=dict(sha256=digest,bytes=package.stat().st_size,firmware_versions=proof['firmware_versions'],
    differing_files_from= differences,separate_linux_files=True,
    stock_firmware_overwritten=False,original_configuration_used=True,
    new_boot_guard=14,linux_trial_started=False)
(ref/'a11-candidate-package.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
