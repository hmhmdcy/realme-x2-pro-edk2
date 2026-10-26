from pathlib import Path
import hashlib, json, os, shutil, subprocess

W = Path('/mnt/e/RealmeX2Pro edk2')
O = Path('/mnt/e/edk2-samurai-out/kernel89')
P = O.parent / 'kernel88'
K = Path('/home/cy122/x2pro-linux/linux')
I = K.parent / 'initramfs'
repo = Path('/home/cy122/edk2-samurai/repo')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not O.exists()
assert not subprocess.check_output(['git','-C',str(repo),'status','--porcelain'],text=True).strip()
head = subprocess.check_output(['git','-C',str(repo),'rev-parse','HEAD'],text=True).strip()
saved = json.loads((P/'preserved-before.json').read_text())
for rel, item in saved['sources'].items():
    assert (K/rel).stat().st_mode & 0o777 == item['mode'], rel
    if rel != 'arch/arm64/boot/dts/qcom/sm8150-samurai.dts': assert sha(K/rel)==item['sha256'],rel
for rel, item in saved['initramfs_files'].items():
    assert sha(I/rel)==item['sha256'] and (I/rel).stat().st_mode & 0o777==item['mode'],rel
for rel, target in saved['initramfs_links'].items(): assert os.readlink(I/rel)==target,rel
for actual, candidate in [('arch/arm64/boot/Image','Image-wifi'),('arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','samurai-wifi.dtb'),('.config','config-wifi'),('usr/initramfs_data.cpio','cpio-before')]:
    assert (K/actual).read_bytes()==(P/candidate).read_bytes(),actual
assert sha(P/'Image-wifi')=='02fbe7e5d20cc2a0f5b55e08511ee9a1a39d2c47516079569fe8dc2368360ea0'
O.mkdir()
fv=repo/'workspace/Build/samurai/RELEASE_GCC5/FV'
blob=repo/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
assert sha(blob)=='872fd9f83382143977c2406c0a869bcac5c051f0f27350ddf3676f043572587b'
for src,name in [(repo/'boot-samurai.img','boot-before.img'),(blob,'firmware-before.dtb'),(fv/'SM8150_UEFI.fd','firmware-before.fd'),(fv/'FVMAIN.Fv','fvmain-before.Fv'),(fv/'FVMAIN_COMPACT.Fv','fvcompact-before.Fv'),(repo/'Platform/Realme/sm8150/FdtBlob_compat/samurai.dtb','compat-before.dtb'),(P/'samurai-wifi.dtb','firmware-after.dtb')]:
    shutil.copyfile(src,O/name)
assert sha(O/'boot-before.img')=='08edf9bcc1c55977169b0a8fd9f963805ba98d0423929e09e17bb9f811ca7405'
source=(W/'reference/kernel79/verify-firmware.py').read_text()
ns={}; exec(source.split('\ndt_audit=')[0],ns)
before=ns['fdt_nodes']((O/'firmware-before.dtb').read_bytes())
after=ns['fdt_nodes']((O/'firmware-after.dtb').read_bytes())
assert before.keys()==after.keys()
changes=[]
for path in before:
    for prop in before[path].keys()|after[path].keys():
        a,b=before[path].get(prop),after[path].get(prop)
        if a!=b: changes.append({'path':path,'property':prop,'before':None if a is None else a.hex(),'after':None if b is None else b.hex()})
assert {(c['path'],c['property']) for c in changes}=={('/soc@0/remoteproc@4080000','status'),('/soc@0/remoteproc@4080000','firmware-name')}
assert after['/soc@0/remoteproc@4080000']['status']==b'okay\0'
assert after['/soc@0/remoteproc@4080000']['firmware-name']==b'qcom/sm8150/realme/samurai/modem.mdt\0'
assert after['/soc@0/wifi@18800000']['status']==b'disabled\0'
(O/'dtb-validation.json').write_text(json.dumps({'only_manual_mpss_enabled':True,'wifi_disabled':True,'changed_properties':changes},indent=2)+'\n')
source=source.replace('kernel79','kernel89').replace('boot-k79-bus.img','boot-k89-mpss.img').replace("version_before='136157b'","version_before='3dd07f4'").replace("version_after='3dd07f4'",f"version_after='{head[:7]}'").replace('i2c1_adapter_only','manual_mpss_only')
(W/'reference/kernel89/verify-firmware.py').write_text(source)
(O/'preparation.json').write_text(json.dumps({'edk2_head':head,'Image_sha256':sha(P/'Image-wifi'),'cpio_sha256':sha(P/'cpio-before'),'sources_preserved':len(saved['sources']),'initramfs_files':len(saved['initramfs_files']),'initramfs_links':len(saved['initramfs_links']),'mpss_manual_start':True,'wifi_disabled':True},indent=2)+'\n')
print('Prepared',head,'MPSS-only firmware; preserved sources/initramfs')
