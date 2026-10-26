from pathlib import Path
import difflib, hashlib, json, shutil, subprocess
root=Path('/mnt/e/RealmeX2Pro edk2')
ref=root/'reference/kernel101'
out=Path('/mnt/e/edk2-samurai-out/kernel101')
k=Path('/home/cy122/x2pro-linux/linux')
init=Path('/home/cy122/x2pro-linux/initramfs')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out/'preparation.json').exists()
assert (k/'.config').read_bytes()==(out/'config-before').read_bytes()
assert (k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts').read_bytes()==(out/'dts-before').read_bytes()
before=json.loads((out/'initramfs-before.json').read_text())
after={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
changed={p for p in before if before[p]!=after.get(p)}
assert changed=={'usr/sbin/samurai-wifi','usr/sbin/samurai-radio-address'}
assert after.keys()-before.keys()=={'usr/sbin/samurai-modem-remoteproc'}
for name in ('samurai-wifi','samurai-radio-address','samurai-modem-remoteproc'):
    assert (init/'usr/sbin'/name).read_bytes()==(ref/name).read_bytes()
exec((ref/'prepare-adsp.py').read_text().split("fw=init/'lib/firmware/qcom/sm8150/realme/samurai'",1)[1].join(["fw=init/'lib/firmware/qcom/sm8150/realme/samurai'",'']))
