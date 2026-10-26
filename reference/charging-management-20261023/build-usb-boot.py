"""Reuse validated389 firmware DT-carrier process; restore shared outputs."""
from pathlib import Path
import hashlib
import json
import shutil

ref=Path(__file__).resolve().parent
root=Path('/mnt/e/edk2-samurai-out')
out=root/'charging-management-20261023/usb-boot'
out.mkdir(mode=0o700,exist_ok=True)
proof=json.loads((ref/'usb-dt-result.json').read_text())
assert proof['passed'] and proof['all_other_properties_byte_exact']
candidate=root/'charging-management-20261023/usb-dt/samurai-charging-usb-private.dtb'
assert hashlib.sha256(candidate.read_bytes()).hexdigest()==proof['dtb_sha256']
baseline=root/'kernel389/boot-partition-k389-icp-platform.img'
assert hashlib.sha256(baseline.read_bytes()).hexdigest()==proof['rollback_boot_sha256']
shutil.copyfile(candidate,out/'samurai-charging-private.dtb')
inputs=out/'candidate-build';inputs.mkdir(mode=0o700,exist_ok=True)
shutil.copyfile(candidate,inputs/'icp.dtb')
(out/'boot-dtb-input-private.json').write_text(json.dumps({'candidate_dtb_sha256':proof['dtb_sha256']}))
tools=out/'firmware-tools';tools.mkdir(mode=0o700,exist_ok=True)
shutil.copyfile(root/'kernel276/firmware-tools/git',tools/'git');(tools/'git').chmod(0o700)
text=(root/'kernel389/generated-boot-builder-private.py').read_text()
changes=[
    ("out = Path('/mnt/e/edk2-samurai-out/kernel389')",'out = Path('+repr(str(out))+')'),
    ('kernel366/boot-partition-k366-icp-dt.img','kernel389/boot-partition-k389-icp-platform.img'),
    ('c3e4e9c85d80c8ec37605cd522cf716525ae5ebe4fa801342dbf7586c292d924',proof['rollback_boot_sha256']),
    ('kernel365/samurai365-private.dtb','kernel389/samurai389-private.dtb'),
    ("(out/'samurai389-private.dtb')","(out/'samurai-charging-private.dtb')"),
    ("(ref/'dt-build-validation.json')","(ref/'usb-dt-result.json')"),
    ("proof['all_other_dt_properties_semantically_preserved']","proof['all_other_properties_byte_exact']"),
    ("dt_changes=[('/soc@0/icp@ac10000', n) for n in ['status','firmware-name','iommus','memory-region','memory-region-names','phandle']]","dt_changes=[(proof['dwc3_node'], 'usb-psy-name')]"),
    ("dt['only_new_nodes']=proof['added_address_only_reservation_nodes']","dt['only_new_nodes']=[]"),
    ("boot_path = out / 'boot-partition-k389-icp-platform.img'","boot_path = out / 'boot-charging-usb-dt.img'"),
    ('report = dict(stage=389,','report = dict(work="charging-management-20261023",'),
    ("    candidate_camss_module_sha256='24fcfa685d07eb8d0e1a0b8356d9ee005e5413faf29c1b384e8c79c364630288',\n",''),
    ("'build-package-validation.json'","'usb-boot-result.json'"),
]
for a,b in changes:
    assert text.count(a)==1,(a,text.count(a));text=text.replace(a,b)
text=text.replace('out.parent',"Path('/mnt/e/edk2-samurai-out')")
compile(text,'generated-usb-boot-builder','exec')
(out/'generated-boot-builder-private.py').write_text(text)
repo=Path('/home/cy122/edk2-samurai/repo')
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV'
outputs=[repo/'boot-samurai.img',fv/'SM8150_UEFI.fd',fv/'FVMAIN.Fv']
saved={p:p.read_bytes() for p in outputs}
backup=out/'outputs-before';backup.mkdir(mode=0o700,exist_ok=True)
for p,b in saved.items():(backup/p.name).write_bytes(b)
try:
    exec(compile(text,'charging-usb-boot-builder','exec'),{'__file__':str(ref/'generated-usb-builder.py')})
finally:
    for p,b in saved.items():p.write_bytes(b)
    assert all(p.read_bytes()==b for p,b in saved.items())
    (out/'output-restoration.json').write_text(json.dumps({'shared_outputs_restored':True}))
