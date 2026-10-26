from pathlib import Path
import json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel147'); ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel147')
s=(out / 'first-runtime-private.txt').read_text().splitlines()
assert s[0].startswith('#147 ') and re.fullmatch('[a-f0-9-]{36}',s[1])
build=json.loads((ref / 'build-package-validation.json').read_text())
assert build['logdump_sha256']+'  /dev/sde32' in s
with tarfile.open(out / 'preflash-private.tar.gz') as archive:
    member=next(m for m in archive if m.name.endswith('partition-check.sha256'))
    prior=archive.extractfile(member).read().decode().splitlines()
for device in ['/dev/sde11','/dev/sda2']:
    expected=next(line for line in prior if line.endswith('  '+device))
    assert expected in s
(out / 'embedded-boot-id-private.txt').write_text(s[1]+'\n')
build['deployed']=True
for p in [ref,out]: (p / 'build-package-validation.json').write_text(json.dumps(build,indent=2)+'\n')
report=dict(stage=147,kernel147_observed=True,logdump_readback_match=True,boot_and_persist_hash_unchanged=True,early_taint=int(s[2]),gpu_runtime_acceptance_pending=True)
(ref / 'first-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
oldref=ref.parent / 'kernel146'; oldout=out.parent / 'kernel146'
old=json.loads((oldref / 'build-package-validation.json').read_text())
old.update(deployed=True,device_fix_accepted=False,candidate_rejected=True,reason='Default fixed-size validation passed pixels but added two delayed CCU READ TRANSLATION faults.')
for p in [oldref,oldout]: (p / 'build-package-validation.json').write_text(json.dumps(old,indent=2)+'\n')
print('K147_BOOT_AND_PARTITION_READBACK_VERIFIED_K146_REJECTED')
