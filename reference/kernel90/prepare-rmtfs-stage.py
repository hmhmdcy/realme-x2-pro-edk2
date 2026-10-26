from pathlib import Path
import difflib, hashlib, json, shutil, subprocess

W=Path('/mnt/e/RealmeX2Pro edk2')
O=Path('/mnt/e/edk2-samurai-out/kernel91')
B=O.parent/'kernel90'
K=Path('/home/cy122/x2pro-linux/linux')
repo=Path('/home/cy122/edk2-samurai/repo')
R=W/'reference/kernel91'
assert not O.exists() and not R.exists()
O.mkdir(); R.mkdir()
blob=repo/'Platform/Realme/sm8150/FdtBlob/samurai/sm8150-realme-samurai.dtb'
assert blob.read_bytes()==(B/'firmware-after.dtb').read_bytes()
assert (repo/'boot-samurai.img').read_bytes()==(B/'boot-k90-wifi.img').read_bytes()
for src,dst in [('boot-k90-wifi.img','boot-before.img'),('firmware-after.fd','firmware-before.fd'),('firmware-after.dtb','firmware-before.dtb'),('fvmain-after.Fv','fvmain-before.Fv'),('fvcompact-after.Fv','fvcompact-before.Fv'),('compat-before.dtb','compat-before.dtb'),('logdump-before.img','logdump-before.img')]:
    shutil.copyfile(B/src,O/dst)
for src,dst in [('.config','config-before'),('usr/initramfs_data.cpio','cpio-before'),('arch/arm64/boot/Image','Image-before'),('arch/arm64/boot/dts/qcom/sm8150-samurai.dts','dts-before')]:
    shutil.copyfile(K/src,O/dst)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(O/'Image-before')=='02fbe7e5d20cc2a0f5b55e08511ee9a1a39d2c47516079569fe8dc2368360ea0'
cfg=K/'.config'; text=cfg.read_text()
assert text.count('CONFIG_QCOM_RMTFS_MEM=m\n')==1
cfg.write_text(text.replace('CONFIG_QCOM_RMTFS_MEM=m\n','CONFIG_QCOM_RMTFS_MEM=y\n'))
dts=K/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'; before=dts.read_text()
needle='\t\t/* hyp_mem, smem_mem and aop_cmd_db are correct as inherited. */'
assert before.count(needle)==1
addition='''\t\t/*
\t\t * Stock sharedmem-uio allocates 2 MiB dynamically with 4 KiB guards,
\t\t * client 1 and HLOS/MSS_MSA RW permissions. Allocate from EFI-described
\t\t * HLOS RAM below 4 GiB; never reuse the MTP address inside this board's TZ.
\t\t */
\t\tsamurai_rmtfs_mem: rmtfs-dynamic {
\t\t\tcompatible = "qcom,rmtfs-mem";
\t\t\tsize = <0x0 0x202000>;
\t\t\talignment = <0x0 0x1000>;
\t\t\talloc-ranges = <0x0 0xc0000000 0x0 0x30000000>;
\t\t\tno-map;
\t\t\tqcom,client-id = <1>;
\t\t\tqcom,use-guard-pages;
\t\t\tqcom,vmid = <QCOM_SCM_VMID_MSS_MSA>;
\t\t};

'''
dts.write_text(before.replace(needle,addition+needle))
(R/'rmtfs-dynamic-dts.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),dts.read_text().splitlines(True),fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts',tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts')))
for name in ('verify-firmware.py','build-firmware.sh'):
    s=(W/'reference/kernel90'/name).read_text().replace('kernel90','kernel91').replace('boot-k90-wifi.img','boot-k91-rmtfs.img').replace('wifi_status_only','rmtfs_dynamic_only')
    (R/name).write_text(s)
(R/'build-kernel.sh').write_text('''#!/bin/bash
set -euo pipefail
cd /home/cy122/x2pro-linux/linux
out=/mnt/e/edk2-samurai-out/kernel91
test ! -e "$out/Image-rmtfs"
make ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- olddefconfig > "$out/olddefconfig.log" 2>&1
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel91/audit-config.py'
make -j8 ARCH=arm64 CROSS_COMPILE=aarch64-linux-gnu- KBUILD_BUILD_VERSION=90 Image qcom/sm8150-samurai.dtb > "$out/build-kernel.log" 2>&1
cmp usr/initramfs_data.cpio "$out/cpio-before"
cp arch/arm64/boot/Image "$out/Image-rmtfs"
cp arch/arm64/boot/dts/qcom/sm8150-samurai.dtb "$out/firmware-after.dtb"
cp .config "$out/config-after"
python3 '/mnt/e/RealmeX2Pro edk2/reference/kernel91/audit-dtb.py'
sha256sum "$out/Image-rmtfs" "$out/firmware-after.dtb" .config usr/initramfs_data.cpio > "$out/build-hashes.txt"
tail -12 "$out/build-kernel.log"
cat "$out/build-hashes.txt"
''')
(R/'audit-config.py').write_text('''from pathlib import Path
import json
O=Path('/mnt/e/edk2-samurai-out/kernel91')
a=(O/'config-before').read_text().splitlines(); b=Path('/home/cy122/x2pro-linux/linux/.config').read_text().splitlines()
assert [x for x in a if x not in b]==['CONFIG_QCOM_RMTFS_MEM=m']
assert [x for x in b if x not in a]==['CONFIG_QCOM_RMTFS_MEM=y']
(O/'config-validation.json').write_text(json.dumps({'only_change':'CONFIG_QCOM_RMTFS_MEM=m -> y'},indent=2)+'\\n')
''')
(R/'audit-dtb.py').write_text('''from pathlib import Path
import json,struct
O=Path('/mnt/e/edk2-samurai-out/kernel91')
ns={};exec(Path('/mnt/e/RealmeX2Pro edk2/reference/kernel91/verify-firmware.py').read_text().split('\\ndt_audit=')[0],ns)
a=ns['fdt_nodes']((O/'firmware-before.dtb').read_bytes());b=ns['fdt_nodes']((O/'firmware-after.dtb').read_bytes())
assert set(b)-set(a)=={'/reserved-memory/rmtfs-dynamic'}
assert set(a)-set(b)==set()
assert all(a[p]==b[p] for p in a)
n=b['/reserved-memory/rmtfs-dynamic']
assert set(n)=={'compatible','size','alignment','alloc-ranges','no-map','qcom,client-id','qcom,use-guard-pages','qcom,vmid'}
assert n['compatible']==b'qcom,rmtfs-mem\\0'
assert struct.unpack('>II',n['size'])==(0,0x202000)
assert struct.unpack('>I',n['qcom,vmid'])==(15,)
assert struct.unpack('>IIII',n['alloc-ranges'])==(0,0xc0000000,0,0x30000000)
(O/'dtb-validation.json').write_text(json.dumps({'only_addition':'/reserved-memory/rmtfs-dynamic','original_nodes_byte_identical':True,'usable_bytes':0x200000,'guard_bytes':0x2000,'client':1,'vmid':15,'mpss_manual_start_preserved':True},indent=2)+'\\n')
''')
print('Prepared stage91: dynamic guarded RMTFS RAM and one built-in config change')
