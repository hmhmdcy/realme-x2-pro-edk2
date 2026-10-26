from pathlib import Path
import hashlib,zipfile,stat,json,subprocess
root=Path('/mnt/e/edk2-samurai-out/rx61')
arc=root/'qcom-14b6fe1-source.zip'
assert hashlib.sha256(arc.read_bytes()).hexdigest()=='ed5b4309139a286f3ef22ad846495bd7dbcb879dce4b4fa66e1d54d3663641a9'
dest=root/'source-pinned'
assert not dest.exists()
with zipfile.ZipFile(arc) as z:
    prefix='qcom-usb-kernel-drivers-14b6fe1ee69cdd9182502629da9192156b9d206a/'
    for info in z.infolist():
        p=Path(info.filename)
        assert not p.is_absolute() and '..' not in p.parts and info.filename.startswith(prefix)
        assert not stat.S_ISLNK(info.external_attr>>16)
    z.extractall(dest)
source=dest/prefix.rstrip('/')
p=source/'src/windows/wdfserial/QCPNP.c'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='fc90dd37159ffac9e6ce21202f9edd436aa73014eedc2c8d1551fca9d51f4f64'
inf=source/'src/windows/wdfserial/qcwdfser.inf'
assert inf.read_bytes()==(root/'qcwdfser-14b6fe1.inf').read_bytes()
patch=Path('/mnt/e/RealmeX2Pro edk2/reference/rx60/eud-preserve-toggle-on-open.candidate.patch')
subprocess.run(['git','apply','--check',str(patch)],cwd=source,check=True)
subprocess.run(['git','apply',str(patch)],cwd=source,check=True)
assert p.read_text()==Path('/mnt/e/edk2-samurai-out/rx60/QCPNP-candidate.c').read_text()
summary=dict(base_commit='14b6fe1ee69cdd9182502629da9192156b9d206a',source_directory=str(source),archive_sha256=hashlib.sha256(arc.read_bytes()).hexdigest(),pinned_inf_sha256=hashlib.sha256(inf.read_bytes()).hexdigest(),candidate_applied_to_complete_source_tree=True,upstream_inf_contains_eud_9505='9505' in inf.read_text().lower(),installed=False)
(root/'source-preparation.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(summary,indent=2))
