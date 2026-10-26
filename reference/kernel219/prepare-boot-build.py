from pathlib import Path
import hashlib,importlib.util,json,subprocess

here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel219')
dtb_dir=private/'candidate-build';dtb=dtb_dir/'factory-modes.dtb';yaml=dtb_dir/'factory-modes.yaml'
proof=json.loads((here/'factory-mode-candidate-build-validation.json').read_text())
assert hashlib.sha256(dtb.read_bytes()).hexdigest()==proof['dtb_sha256']
p=subprocess.run(['dtc','-O','yaml','-o',str(yaml),str(dtb_dir/'factory-modes.pp.dts')],capture_output=True,timeout=60)
(dtb_dir/'yaml-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
spec=importlib.util.spec_from_file_location('fdt_compare219',here.parent/'kernel211/fdt_compare.py');fdt=importlib.util.module_from_spec(spec);spec.loader.exec_module(fdt)
parse=fdt.parser()
before=parse((private.parent/'kernel211/sensor-domain-dtb/sensor-domain.dtb').read_bytes());after=parse(dtb.read_bytes())
semantic=fdt.compare(before,after,yaml)
assert semantic['only_old_nodes']==semantic['only_new_nodes']==[]
assert semantic['remaining_changed_properties']==[dict(path='/soc@0/cci@ac4b000/i2c-bus@1/camera@10/port/endpoint',property='link-frequencies')]
report=dict(stage=219,candidate_dtb_sha256=proof['dtb_sha256'],**semantic)
(here/'mode-dtb-validation.json').write_text(json.dumps(report,indent=2)+'\n')
text=(here.parent/'kernel211/build-package.py').read_text()
changes=[
    ("out = Path('/mnt/e/edk2-samurai-out/kernel211')","out = Path('/mnt/e/edk2-samurai-out/kernel219')"),
    ("'sensor-domain-dtb-validation.json'","'mode-dtb-validation.json'"),
    ("'sensor-domain-dtb/sensor-domain.dtb'","'candidate-build/factory-modes.dtb'"),
    ("'sensor-domain-dtb/sensor-domain.yaml'","'candidate-build/factory-modes.yaml'"),
    ("'kernel210/boot-partition-k210-front.img'","'kernel211/boot-partition-k211-sensor-domain.img'"),
    ('89242ade44ddaebf2b124d3bb5e9bd6597d0c818488b1e84d719d36a5a5023c0','c3bf043f2eea0c5f8e42cc8cac621ccfba023b181e400d0919174b87e3d37ba6'),
    ("'boot-partition-k211-sensor-domain.img'","'boot-partition-k219-front-modes.img'"),
    ('report = dict(stage=211,','report = dict(stage=219,'),
    ('from fdt_compare import compare','compare = fdt_compare_function'),
]
for old,new in changes:
    assert old in text,old;text=text.replace(old,new)
compile(text,'boot-builder219','exec')
(here/'build-package.py').write_text(text)
print(json.dumps(report))
