"""Build a DT-only firmware candidate, preserving the deployed code and Image183."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel270')
repo=Path('/home/cy122/edk2-samurai/repo')
proof=json.loads((R/'telephoto-board-build-validation.json').read_text())
assert proof['all_other_existing_peripheral_properties_preserved'] and proof['new_nodes']==10
dt=json.loads((P/'telephoto-dtb-semantic-private.json').read_text())
dt['candidate_dtb_sha256']=proof['dtb_sha256'];(P/'boot-dtb-input-private.json').write_text(json.dumps(dt,indent=2)+'\n')
oldproof=json.loads((R.parent/'kernel267/build-package-validation.json').read_text())
old=P.parent/'kernel267/boot-partition-k267-common-camera.img'
assert hashlib.sha256(old.read_bytes()).hexdigest()==oldproof['boot_sha256']
candidate=P/'candidate-build';candidate.mkdir(mode=0o700)
shutil.copyfile('/home/cy122/x2pro-linux/camera270-build-r1/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',candidate/'telephoto.dtb')
shutil.copyfile(P/'telephoto.yaml',candidate/'telephoto.yaml')
tools=P/'firmware-tools';tools.mkdir(mode=0o700)
shim=P.parent/'kernel267/firmware-tools/git';assert '5c80582' in shim.read_text()
shutil.copyfile(shim,tools/'git');(tools/'git').chmod(0o700)
text=(R.parent/'kernel219/build-package.py').read_text()
changes=[
 ("out = Path('/mnt/e/edk2-samurai-out/kernel219')","out = Path('/mnt/e/edk2-samurai-out/kernel270')"),
 ("(ref / 'mode-dtb-validation.json')","(out / 'boot-dtb-input-private.json')"),
 ("out / 'candidate-build/factory-modes.dtb'","out / 'candidate-build/telephoto.dtb'"),
 ("out / 'candidate-build/factory-modes.yaml'","out / 'candidate-build/telephoto.yaml'"),
 ('kernel211/boot-partition-k211-sensor-domain.img','kernel267/boot-partition-k267-common-camera.img'),
 ('c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6',oldproof['boot_sha256']),
 ("boot-partition-k219-front-modes.img'\nassert not boot_path","boot-partition-k270-telephoto.img'\nassert not boot_path"),
 ('report = dict(stage=219,','report = dict(stage=270,'),
 ('82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58','ff9fdfa346249d836c0f830c9ea2480b6b06b280089007a054a6d2a0514f5822'),
 ("env.update(PATH='/home/cy122/.local/bin:' + env['PATH']","env.update(PATH=str(out/'firmware-tools') + ':/home/cy122/.local/bin:' + env['PATH']")]
for a,b in changes:
 assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
(P/'generated-boot-builder-private.py').write_text(text)
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV'
outputs=[repo/'boot-samurai.img',fv/'SM8150_UEFI.fd',fv/'FVMAIN.Fv']
saved={str(p):p.read_bytes() for p in outputs}
backup=P/'firmware-outputs-before';backup.mkdir(mode=0o700)
for p in outputs:(backup/p.name).write_bytes(saved[str(p)])
spec=importlib.util.spec_from_file_location('fdt',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
try:exec(compile(text,'boot-builder270','exec'),dict(__file__=str(R/'build-package-generated.py'),fdt_compare_function=f.compare))
finally:
 for p in outputs:p.write_bytes(saved[str(p)])
 assert all(p.read_bytes()==saved[str(p)] for p in outputs)
 (P/'firmware-output-restoration-private.json').write_text(json.dumps(dict(all_three_generated_outputs_restored=True))+'\n')
print(json.dumps(dict(stage=270,dt_only_boot_built=True,rollback_boot267_retained=True,phone_unchanged=True)))
