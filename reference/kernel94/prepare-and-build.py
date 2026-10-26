from pathlib import Path
import hashlib,json,shutil,subprocess
out=Path('/mnt/e/edk2-samurai-out/kernel94')
prev=out.parent/'kernel93'
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel94')
kernel=Path('/home/cy122/x2pro-linux/linux')
root=kernel.parent/'initramfs'
if not out.exists():
    out.mkdir(mode=0o700)
    for src,name in [(kernel/'arch/arm64/boot/Image','Image-before'),(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb','dtb-before'),(kernel/'usr/initramfs_data.cpio','cpio-before'),(kernel/'.config','config-before'),(root/'init','init-before')]:shutil.copyfile(src,out/name)
else:
    # The first preparation stopped at the config audit before build or init edits.
    assert (root/'init').read_bytes()==(out/'init-before').read_bytes()
    assert not (out/'Image-connectivity').exists()
assert (out/'Image-before').read_bytes()==(prev/'Image-connectivity').read_bytes()
assert (out/'cpio-before').read_bytes()==(prev/'cpio-after').read_bytes()
assert (out/'dtb-before').read_bytes()==(prev/'dtb-connectivity').read_bytes()
subprocess.run(['scripts/config','--module','BT_HCIUART'],cwd=kernel,check=True)
with (out/'olddefconfig.log').open('w') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
def config(p):return dict(line.split('=',1) for line in p.read_text().splitlines() if line.startswith('CONFIG_'))
a,b=config(out/'config-before'),config(kernel/'.config')
changes={key:[a.get(key),b.get(key)] for key in a.keys()|b.keys() if a.get(key)!=b.get(key)}
assert changes=={key:['y','m'] for key in ('CONFIG_BT_HCIUART','CONFIG_BT_BCM','CONFIG_BT_QCA')},changes
with (out/'module-build.log').open('w') as log:
    subprocess.run(['make','-j8','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','KBUILD_BUILD_VERSION=93','vmlinux'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
    # Keep all dependent .ko targets in one modpost invocation, separate from vmlinux.
    subprocess.run(['make','-j8','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','KBUILD_BUILD_VERSION=93','drivers/bluetooth/hci_uart.ko','drivers/bluetooth/btbcm.ko','drivers/bluetooth/btqca.ko'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
module=kernel/'drivers/bluetooth/hci_uart.ko'
info=subprocess.check_output(['modinfo',str(module)],text=True)
deps=next(line.split(':',1)[1].strip() for line in info.splitlines() if line.startswith('depends:'))
assert set(deps.split(','))=={'btbcm','btqca'},info
assert '7.3.0-rc6-rmx1931-samurai+ ' in info
(out/'module-info.txt').write_text(info)
target=root/'lib/modules/samurai';target.mkdir(parents=True,exist_ok=True)
for name in ('btbcm','btqca','hci_uart'):
    src=kernel/f'drivers/bluetooth/{name}.ko'
    assert not (target/f'{name}.ko').exists()
    shutil.copyfile(src,target/f'{name}.ko')
    shutil.copyfile(src,out/f'{name}.ko')
service=root/'usr/sbin/samurai-bluetooth';assert not service.exists()
service.write_bytes((ref/'samurai-bluetooth').read_bytes());service.chmod(0o755)
init=root/'init';before=init.read_text()
anchor='\n  echo "[wifi] startup exit=$?; see /run/samurai-wifi-boot.log" > /dev/kmsg ) &\n'
assert before.count(anchor)==1
addition='\n# Bluetooth UART loads after Wi-Fi readiness; USB remains independent.\n( /usr/sbin/samurai-bluetooth start > /run/samurai-bluetooth-boot.log 2>&1;\n  echo "[bluetooth] startup exit=$?; see /run/samurai-bluetooth-boot.log" > /dev/kmsg ) &\n'
init.write_text(before.replace(anchor,anchor+addition))
with (out/'build-kernel.log').open('w') as log:subprocess.run(['make','-j8','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','KBUILD_BUILD_VERSION=93','Image','qcom/sm8150-samurai.dtb'],cwd=kernel,stdout=log,stderr=subprocess.STDOUT,check=True)
for src,name in [(kernel/'arch/arm64/boot/Image','Image-connectivity'),(kernel/'usr/initramfs_data.cpio','cpio-after'),(kernel/'.config','config-after')]:shutil.copyfile(src,out/name)
assert (kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb').read_bytes()==(out/'dtb-before').read_bytes()
shutil.copyfile(out/'dtb-before',out/'dtb-connectivity')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=dict(config_changes=changes,dtb_byte_identical=True,driver_still_included=True,module_dependencies=sorted(deps.split(',')),hci_uart_sha256=sha(module),kernel_build=93,image_sha256=sha(out/'Image-connectivity'),cpio_sha256=sha(out/'cpio-after'))
(out/'build-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
