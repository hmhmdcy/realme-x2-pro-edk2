from pathlib import Path
import ast,hashlib,json,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel158');out=Path('/mnt/e/edk2-samurai-out/kernel158');old=ref.parent/'kernel157'
names=['capture-startup.py','display-power.py','capture-display-cycles.py','verify-runtime.py','capture-boot-timing.py']
for name in names:
    s=(old/name).read_text().replace('kernel157','kernel158').replace('k157','k158').replace('K157','K158').replace('#157 ','#158 ').replace('stage=157','stage=158').replace('kernel_build=157','kernel_build=158')
    if name=='capture-startup.py':s=s.replace('/var/lib/samurai/k158-preflash/boot-id-private.txt','/var/lib/samurai/k158-source-ram/boot-id-private.txt')
    if name=='verify-runtime.py':
        s=s.replace('/var/lib/samurai/k158-preflash/boot-id-private.txt','/var/lib/samurai/k158-source-ram/boot-id-private.txt')
        s=s.replace('/var/lib/samurai/k158-preflash/partition-check.sha256','/var/lib/samurai/k157-preflash/partition-check.sha256')
        s=s.replace('/var/lib/samurai/k158-preflash/old132-module-tree.sha256','/var/lib/samurai/k157-preflash/old132-module-tree.sha256')
        s=s.replace('hardware_display_root_cause_confirmed=False','preservation_reference_from_current156_before157_flash=True,hardware_display_root_cause_confirmed=False')
    if name in ['capture-startup.py','capture-display-cycles.py']:
        s=s.replace("dict(dpu_timeouts=", "dict(kms_init_failures='kms hw init failed',dpu_timeouts=")
    dest=ref/name;assert not dest.exists();dest.write_text(s);ast.parse(s)
with tarfile.open(out/'postboot-tools-private.tar','w') as t:
    for name in names:t.add(ref/name,arcname=name)
    t.add(ref/'build-package-validation.json',arcname='build-package-validation.json')
result=dict(stage=158,current_source_ram_provenance_explicit=True,
    protected_data_reference_from156_before157_flash=True,first_kms_failure_is_a_gate=True,
    archive_sha256=hashlib.sha256((out/'postboot-tools-private.tar').read_bytes()).hexdigest())
(ref/'postboot-tools-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
