from pathlib import Path
import hashlib, json, shutil, subprocess

W=Path('/mnt/e/RealmeX2Pro edk2')
O=Path('/mnt/e/edk2-samurai-out/kernel90')
B=O.parent/'kernel89'
K=Path('/home/cy122/x2pro-linux/linux')
repo=Path('/home/cy122/edk2-samurai/repo')
R=W/'reference/kernel90'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert not O.exists() and not R.exists()
O.mkdir();R.mkdir()
blob=repo/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
assert blob.read_bytes()==(B/'firmware-after.dtb').read_bytes()
assert (repo/'boot-samurai.img').read_bytes()==(B/'boot-k89-mpss.img').read_bytes()
dts=K/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
src=dts.read_text(); old='&wifi {\n\tstatus = "disabled";\n};'
assert src.count(old)==1
(O/'dts-before').write_bytes(dts.read_bytes())
dts.write_text(src.replace(old,'&wifi {\n\tstatus = "okay";\n};'))
subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','-j8','qcom/sm8150-samurai.dtb'],cwd=K,check=True,stdout=(O/'dtb-build.log').open('w'),stderr=subprocess.STDOUT)
shutil.copyfile(K/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb',O/'firmware-after.dtb')
for oldname,newname in [('boot-k89-mpss.img','boot-before.img'),('firmware-after.fd','firmware-before.fd'),('firmware-after.dtb','firmware-before.dtb'),('fvmain-after.Fv','fvmain-before.Fv'),('fvcompact-after.Fv','fvcompact-before.Fv'),('compat-before.dtb','compat-before.dtb')]:shutil.copyfile(B/oldname,O/newname)
base=(W/'reference/kernel89/verify-firmware.py').read_text()
ns={};exec(base.split('\ndt_audit=')[0],ns)
a=ns['fdt_nodes']((O/'firmware-before.dtb').read_bytes());b=ns['fdt_nodes']((O/'firmware-after.dtb').read_bytes())
assert a.keys()==b.keys()
changes=[(path,prop) for path in a for prop in a[path].keys()|b[path].keys() if a[path].get(prop)!=b[path].get(prop)]
assert changes==[('/soc@0/wifi@18800000','status')],changes
assert b['/soc@0/wifi@18800000']['status']==b'okay\0'
(O/'dtb-validation.json').write_text(json.dumps({'only_wifi_status_enabled':True,'changes':changes,'mpss_auto_boot_false_preserved':True},indent=2)+'\n')
s=base.replace('kernel89','kernel90').replace('boot-k89-mpss.img','boot-k90-wifi.img').replace("version_before='3dd07f4'","version_before='f23a9f8'").replace('manual_mpss_only','wifi_status_only')
(R/'verify-firmware.py').write_text(s)
s=(W/'reference/kernel89/build-firmware.sh').read_text().replace('kernel89','kernel90').replace('boot-k89-mpss.img','boot-k90-wifi.img')
s=s.replace('test -z "$(git status --porcelain)"','test "$(git status --porcelain)" = " M Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb"')
(R/'build-firmware.sh').write_text(s)
assert sha(K/'arch/arm64/boot/Image')=='02fbe7e5d20cc2a0f5b55e08511ee9a1a39d2c47516079569fe8dc2368360ea0'
subprocess.run(['git','-C',str(K),'diff','--','arch/arm64/boot/dts/qcom/sm8150-samurai.dts'],check=True,stdout=(R/'wifi-mpss-dts.patch').open('w'))
print('Wi-Fi stage: DT-only status change, Image #89 preserved')
