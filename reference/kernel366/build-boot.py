"""Rebuild the proven EDK2 package with exactly the verified365 DT changed."""
from pathlib import Path
import hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;repo=Path('/home/cy122/edk2-samurai/repo')
proof=json.loads((HERE.parent/'kernel365/dt-build-validation.json').read_text());assert proof['passed'] and proof['icp_disabled']
assert json.loads((HERE.parent/'kernel365/postboot-validation.json').read_text())['dt_only_update_effective'] is False
dtb=P.parent/'kernel365/samurai365-private.dtb';assert hashlib.sha256(dtb.read_bytes()).hexdigest()==proof['dtb_sha256']
(P/'boot-dtb-input-private.json').write_text(json.dumps(dict(candidate_dtb_sha256=proof['dtb_sha256'])))
candidate=P/'candidate-build';candidate.mkdir(mode=0o700);shutil.copyfile(dtb,candidate/'icp.dtb')
tools=P/'firmware-tools';tools.mkdir(mode=0o700);shutil.copyfile(P.parent/'kernel276/firmware-tools/git',tools/'git');(tools/'git').chmod(0o700)
s=(P.parent/'kernel276/generated-boot-builder-private.py').read_text()
changes=[("out = Path('/mnt/e/edk2-samurai-out/kernel276')","out = Path('/mnt/e/edk2-samurai-out/kernel366')"),
 ('candidate-build/cci-io.dtb','candidate-build/icp.dtb'),('kernel275/boot-partition-k275-main-lens.img','kernel276/boot-partition-k276-cci-io.img'),
 ('5f023faa698c1c7c84c04c5c40a341e7c212becde97e7d53d49c59944ae13d42','0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64'),
 ("boot_path = out / 'boot-partition-k276-cci-io.img'","boot_path = out / 'boot-partition-k366-icp-dt.img'"),
 ('report = dict(stage=276, kernel_build=183,','report = dict(stage=366, kernel_build=363,'),
 ("ref.parent / 'kernel183/build-package-validation.json'","ref.parent / 'kernel365/boot-package-validation.json'"),
 ("candidate_camss_sha256='ff9fdfa346249d836c0f830c9ea2480b6b06b280089007a054a6d2a0514f5822'","candidate_camss_note_sha256='1e78064da626b1dd91fc82c183abd96b5fb98f95e11a8eb7b760b9a138095dae'")]
for a,b in changes:assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
a=s.index('oldtree = fdt_nodes(');b=s.index('\ndef normalize(',a)
s=s[:a]+'''assert old['modules'][dt_guid]['sections'][0][1] == (out.parent/'kernel365/dtb-before-private.dtb').read_bytes()
assert dtb == (out.parent/'kernel365/samurai365-private.dtb').read_bytes()
proof=json.loads((ref.parent/'kernel365/dt-build-validation.json').read_text())
assert proof['passed'] and proof['all_existing_phandle_references_preserve_target_paths']
dt_changes=[('/reserved-memory/memory@9ab00000','phandle')]
dt['only_new_nodes']=['/soc@0/icp@ac10000']
''' +s[b:]
(P/'generated-boot-builder-private.py').write_text(s)
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV';outputs=[repo/'boot-samurai.img',fv/'SM8150_UEFI.fd',fv/'FVMAIN.Fv'];saved={str(p):p.read_bytes() for p in outputs}
backup=P/'firmware-outputs-before';backup.mkdir(mode=0o700)
for p in outputs:(backup/p.name).write_bytes(saved[str(p)])
try:exec(compile(s,'boot-builder366','exec'),dict(__file__=str(HERE/'build-package-generated.py')))
finally:
 for p in outputs:p.write_bytes(saved[str(p)])
 assert all(p.read_bytes()==saved[str(p)] for p in outputs)
 (P/'firmware-output-restoration-private.json').write_text(json.dumps(dict(all_three_generated_outputs_restored=True))+'\n')
