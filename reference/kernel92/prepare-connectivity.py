from pathlib import Path
import difflib, hashlib, json, shutil, subprocess, tarfile

root = Path('/home/cy122/x2pro-linux')
kernel = root / 'linux'
initramfs = root / 'initramfs'
out = Path('/mnt/e/edk2-samurai-out/kernel92')
ref = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel92')
old = out.parent / 'kernel91'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (out / 'initramfs-before.tar').exists()
assert sha(kernel / 'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb') == 'e7f217554f09f4614feff7e7b1317e9313b68ed0a773a4a0d8cd930f06374ded'
subprocess.run(['tar', '-C', str(initramfs), '-cf', str(out/'initramfs-before.tar'), '.'], check=True)
def manifest(tree):
    return {str(p.relative_to(tree)): {'mode':p.lstat().st_mode, 'sha256':sha(p)}
            for p in tree.rglob('*') if p.is_file() and not p.is_symlink()}
before = manifest(initramfs)
(out/'initramfs-before.json').write_text(json.dumps(before, indent=2)+'\n')
shutil.copyfile(kernel/'.config', out/'config-before')
dts = kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
shutil.copyfile(dts, out/'dts-before')
shutil.copyfile(kernel/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb', out/'dtb-before')
shutil.copyfile(kernel/'usr/initramfs_data.cpio', out/'cpio-before')

extra = '''
/* Session92: same-handset Android UART13 and NQ-NCI wiring. */
&gpi_dma1 { status = "okay"; };
&qupv3_id_1 { status = "okay"; };

&tlmm {
    samurai_bt_uart_default: samurai-bt-uart-default-state {
        pins = "gpio43", "gpio44", "gpio45", "gpio46";
        function = "qup13";
        drive-strength = <2>;
        bias-disable;
    };
    samurai_nfc_irq_default: samurai-nfc-irq-default-state {
        pins = "gpio47";
        function = "gpio";
        drive-strength = <2>;
        bias-disable;
        input-enable;
    };
};

&uart13 {
    status = "okay";
    pinctrl-names = "default";
    pinctrl-0 = <&samurai_bt_uart_default>;
    bluetooth {
        compatible = "qcom,wcn3990-bt";
        /* Logic rail shares the existing WCN supply; no voltage is changed. */
        vddio-supply = <&vreg_l1a_0p75>;
        vddxo-supply = <&vreg_l7a_1p8>;
        vddrf-supply = <&vreg_l2c_1p3>;
        vddch0-supply = <&vreg_l11c_3p3>;
        max-speed = <3200000>;
    };
};

&i2c9 {
    status = "okay";
    clock-frequency = <400000>;
    nfc@28 {
        compatible = "nxp,nxp-nci-i2c";
        reg = <0x28>;
        interrupt-parent = <&tlmm>;
        interrupts = <47 IRQ_TYPE_LEVEL_HIGH>;
        enable-gpios = <&tlmm 36 GPIO_ACTIVE_HIGH>;
        firmware-gpios = <&tlmm 48 GPIO_ACTIVE_HIGH>;
        pinctrl-names = "default";
        pinctrl-0 = <&samurai_nfc_irq_default>;
    };
};
'''
original = dts.read_text()
assert 'samurai_bt_uart_default' not in original
dts.write_text(original+extra)
(ref/'connectivity-dts.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), dts.read_text().splitlines(True), fromfile='a/arch/arm64/boot/dts/qcom/sm8150-samurai.dts', tofile='b/arch/arm64/boot/dts/qcom/sm8150-samurai.dts')))
src = out/'rmtfs-cow-src'
shutil.copytree(old/'rmtfs-cow-src', src)
main = src/'rmtfs.c'
original = main.read_text()
assert original.count('storage_init("/tmp/k91-nv", true, false)') == 1
main.write_text(original.replace('storage_init("/tmp/k91-nv", true, false)', 'storage_init("/run/samurai-wifi/nv", true, false)'))
(ref/'rmtfs-runtime-root.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True), main.read_text().splitlines(True), fromfile='a/rmtfs.c', tofile='b/rmtfs.c')))
qrtr = out.parent/'kernel88/qrtr'
subprocess.run(['aarch64-linux-gnu-gcc','-O2','-Wall','-Werror=format','-static','-I'+str(qrtr/'include'),'-I'+str(qrtr/'lib'),'-I'+str(src), str(src/'rmtfs.c'),str(src/'qmi_rmtfs.c'),str(src/'rproc-disabled.c'),str(src/'storage.c'),str(src/'sharedmem.c'),str(qrtr/'lib/qrtr.c'),str(qrtr/'lib/qmi.c'),str(qrtr/'lib/logging.c'),'-o',str(out/'rmtfs-cow')],check=True)
tools = {'samurai-rmtfs-cow':out/'rmtfs-cow', 'samurai-tqftpserv':old/'tqftpserv-ram-probe',
         'qrtr-lookup':out.parent/'kernel88/qrtr-lookup', 'wpa_supplicant':old/'wpa_supplicant',
         'wpa_cli':old/'wpa_cli', 'iw':out.parent/'kernel90/iw'}
assert sha(tools['samurai-tqftpserv']) == 'd3a19b2f2daa1c85345182095510ee6d2e5db065118855c8938d9ad7d82dff4e'
assert sha(tools['wpa_supplicant']) == '39bee3e48a11407adea4e7cd415e48c2b6409b75b6c133df787341991d93d5fa'
for name, source in tools.items():
    target = initramfs/'usr/sbin'/name
    assert not target.exists()
    shutil.copyfile(source, target); target.chmod(0o755)
target = initramfs/'usr/sbin/samurai-wifi'
shutil.copyfile(ref/'samurai-wifi', target); target.chmod(0o755)
config = initramfs/'etc/samurai-wifi'
config.mkdir()
lines = (out/'modem-runtime-sha256.txt').read_text().splitlines()
assert len(lines) == 34
(config/'modem-sha256.txt').write_text('\n'.join(f'{d}  {Path(n).name}' for d,n in (s.split() for s in lines))+'\n')
(config/'wpa-empty.conf').write_text('ctrl_interface=/run/samurai-wifi/wpa-control\n')
fw = initramfs/'lib/firmware/ath10k/WCN3990/hw1.0'
fw.mkdir(parents=True)
for name in ('board.bin','firmware-5.bin'): shutil.copyfile(old/name, fw/name)
assert sha(out/'bluetooth-firmware.tar') == '983df773f4ebf6453905be797a892e468263a6e2799f293179b7decceb6f13a2'
bt = initramfs/'lib/firmware/qca'
bt.mkdir()
bt_manifest = {n:d for d,n in (s.split() for s in (out/'bluetooth-sha256.txt').read_text().splitlines())}
with tarfile.open(out/'bluetooth-firmware.tar') as source:
    for name in ('crbtfw11.tlv','crbtfw20.tlv','crbtfw21.tlv','crnv11.bin','crnv20.bin','crnv21.bin'):
        m = source.getmember('./'+name)
        assert m.isfile()
        data = source.extractfile(m).read()
        assert hashlib.sha256(data).hexdigest() == bt_manifest[name]
        (bt/name).write_bytes(data)
init = initramfs/'init'
original = init.read_text()
needle = '/usr/sbin/samurai-usb start &\n'
assert original.count(needle) == 1
init.write_text(original.replace(needle,needle+'\n# Wi-Fi firmware/NV copies and services remain in RAM; USB starts independently.\n( /usr/sbin/samurai-wifi start > /run/samurai-wifi-boot.log 2>&1;\n  echo "[wifi] startup exit=$?; see /run/samurai-wifi-boot.log" > /dev/kmsg ) &\n'))
after = manifest(initramfs)
assert [p for p in before if before[p] != after[p]] == ['init']
(out/'initramfs-after.json').write_text(json.dumps(after, indent=2)+'\n')
(out/'tools-sha256.json').write_text(json.dumps({n:sha(p) for n,p in tools.items()},indent=2)+'\n')
print('Prepared UART13/NFC9 DT and Wi-Fi RAM startup; original initramfs files preserved except init startup insertion')
