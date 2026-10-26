"""Build the actual EDK2 DT carrier using the verified366 process; do not deploy."""
from pathlib import Path
import hashlib,json,shutil
import host
HERE=Path(__file__).resolve().parent;P=host.PRIVATE;repo=Path('/home/cy122/edk2-samurai/repo')
proof=json.loads((HERE/'dt-build-validation.json').read_text());assert proof['passed'] and proof['board_icp_enabled_in_candidate']
assert json.loads((HERE/'binding-validation.json').read_text())['passed']
dtb=P/'samurai389-private.dtb';assert hashlib.sha256(dtb.read_bytes()).hexdigest()==proof['dtb_sha256']
(P/'boot-dtb-input-private.json').write_text(json.dumps(dict(candidate_dtb_sha256=proof['dtb_sha256'])))
candidate=P/'candidate-build';candidate.mkdir(mode=0o700);shutil.copyfile(dtb,candidate/'icp.dtb')
tools=P/'firmware-tools';tools.mkdir(mode=0o700);shutil.copyfile(P.parent/'kernel276/firmware-tools/git',tools/'git');(tools/'git').chmod(0o700)
old=json.loads((HERE.parent/'kernel366/build-package-validation.json').read_text());baseline=P.parent/'kernel366/boot-partition-k366-icp-dt.img'
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==old['boot_sha256']
s=(P.parent/'kernel366/generated-boot-builder-private.py').read_text()
changes=[("out = Path('/mnt/e/edk2-samurai-out/kernel366')","out = Path('/mnt/e/edk2-samurai-out/kernel389')"),
 ('kernel276/boot-partition-k276-cci-io.img','kernel366/boot-partition-k366-icp-dt.img'),
 ('0d6bbc0255fc7a44340b2c2c6a20f2bfa807f683f69dd20a3fb130d961dc4c64',old['boot_sha256']),
 ("(out.parent/'kernel365/dtb-before-private.dtb')","(out.parent/'kernel365/samurai365-private.dtb')"),
 ("dtb == (out.parent/'kernel365/samurai365-private.dtb')","dtb == (out/'samurai389-private.dtb')"),
 ("(ref.parent/'kernel365/dt-build-validation.json')","(ref/'dt-build-validation.json')"),
 ("proof['all_existing_phandle_references_preserve_target_paths']","proof['all_other_dt_properties_semantically_preserved']"),
 ("dt_changes=[('/reserved-memory/memory@9ab00000','phandle')]","dt_changes=[('/soc@0/icp@ac10000', n) for n in ['status','firmware-name','iommus','memory-region','memory-region-names','phandle']]"),
 ("dt['only_new_nodes']=['/soc@0/icp@ac10000']","dt['only_new_nodes']=proof['added_address_only_reservation_nodes']"),
 ("boot-partition-k366-icp-dt.img'","boot-partition-k389-icp-platform.img'"),
 ('report = dict(stage=366,','report = dict(stage=389,'),
 ("new_camera_nodes=dt['only_new_nodes']","added_iova_reservation_nodes=dt['only_new_nodes']"),
 ("candidate_camss_note_sha256='1e78064da626b1dd91fc82c183abd96b5fb98f95e11a8eb7b760b9a138095dae'","candidate_camss_module_sha256='24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288'")]
# Apply the output-filename substitution only to its assignment, preserving rollback input.
for a,b in changes:
 if a=="boot-partition-k366-icp-dt.img'":
  a="boot_path = out / 'boot-partition-k366-icp-dt.img'";b="boot_path = out / 'boot-partition-k389-icp-platform.img'"
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
compile(s,'generated-boot-builder389','exec');(P/'generated-boot-builder-private.py').write_text(s)
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV';outputs=[repo/'boot-samurai.img',fv/'SM8150_UEFI.fd',fv/'FVMAIN.Fv'];saved={str(p):p.read_bytes() for p in outputs}
backup=P/'firmware-outputs-before';backup.mkdir(mode=0o700)
for p in outputs:(backup/p.name).write_bytes(saved[str(p)])
try:exec(compile(s,'boot-builder389','exec'),dict(__file__=str(HERE/'build-package-generated.py')))
finally:
 for p in outputs:p.write_bytes(saved[str(p)])
 assert all(p.read_bytes()==saved[str(p)] for p in outputs)
 (P/'firmware-output-restoration-private.json').write_text(json.dumps(dict(all_three_generated_outputs_restored=True))+'\n')
