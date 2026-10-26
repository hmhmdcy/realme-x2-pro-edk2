"""Reuse the verified DT-only firmware builder, comparing this candidate to actual boot275."""
from pathlib import Path
import hashlib,importlib.util,json,shutil
import host
R=Path(__file__).resolve().parent;P=host.PRIVATE;repo=Path('/home/cy122/edk2-samurai/repo')
proof=json.loads((R/'board-validation.json').read_text());assert proof['shared_cci_io_supply_matches_sensor_io'] and proof['new_nodes']==0
dt=json.loads((P/'cci-board-semantic-private.json').read_text());dt['candidate_dtb_sha256']=proof['dtb_sha256'];(P/'boot-dtb-input-private.json').write_text(json.dumps(dt,indent=2)+'\n')
oldproof=json.loads((R.parent/'kernel275/build-package-validation.json').read_text());old=P.parent/'kernel275/boot-partition-k275-main-lens.img';assert hashlib.sha256(old.read_bytes()).hexdigest()==oldproof['boot_sha256']
candidate=P/'candidate-build';candidate.mkdir(mode=0o700);shutil.copyfile('/home/cy122/x2pro-linux/camera276-build-r1/arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',candidate/'cci-io.dtb');shutil.copyfile(P/'cci-board.yaml',candidate/'cci-io.yaml')
tools=P/'firmware-tools';tools.mkdir(mode=0o700);shutil.copyfile(P.parent/'kernel275/firmware-tools/git',tools/'git');(tools/'git').chmod(0o700)
text=(P.parent/'kernel275/generated-boot-builder-private.py').read_text()
changes=[("out = Path('/mnt/e/edk2-samurai-out/kernel275')","out = Path('/mnt/e/edk2-samurai-out/kernel276')"),('candidate-build/lens.dtb','candidate-build/cci-io.dtb'),('candidate-build/lens.yaml','candidate-build/cci-io.yaml'),("boot_path = out / 'boot-partition-k275-main-lens.img'","boot_path = out / 'boot-partition-k276-cci-io.img'"),('kernel273/boot-partition-k273-main-camera.img','kernel275/boot-partition-k275-main-lens.img'),('dd4c34e4f18a4292cb70dd9b3d87ad710ce4f6e4e4048fe85c7b94eee911d475',oldproof['boot_sha256']),('report = dict(stage=275,','report = dict(stage=276,'),
 ('{("/soc@0/cci@ac4a000/i2c-bus@0/camera@10", "afvdd-supply"), ("/soc@0/cci@ac4a000/i2c-bus@0/camera@10", "lens-focus")}','{("/soc@0/cci@ac4a000", "vddio-supply"), ("/soc@0/cci@ac4b000", "vddio-supply")}')]
for a,b in changes:assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
(P/'generated-boot-builder-private.py').write_text(text)
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV';outputs=[repo/'boot-samurai.img',fv/'SM8150_UEFI.fd',fv/'FVMAIN.Fv'];saved={str(p):p.read_bytes() for p in outputs};backup=P/'firmware-outputs-before';backup.mkdir(mode=0o700)
for p in outputs:(backup/p.name).write_bytes(saved[str(p)])
spec=importlib.util.spec_from_file_location('fdt276',R.parent/'kernel211/fdt_compare.py');f=importlib.util.module_from_spec(spec);spec.loader.exec_module(f)
try:exec(compile(text,'boot-builder276','exec'),dict(__file__=str(R/'build-package-generated.py'),fdt_compare_function=f.compare))
finally:
 for p in outputs:p.write_bytes(saved[str(p)])
 assert all(p.read_bytes()==saved[str(p)] for p in outputs)
 (P/'firmware-output-restoration-private.json').write_text(json.dumps(dict(all_three_generated_outputs_restored=True))+'\n')
