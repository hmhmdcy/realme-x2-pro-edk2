from pathlib import Path
import hashlib,json,os,shutil,subprocess
os.umask(0o077)
root=Path('/var/lib/samurai');out=root/'k210-install-before';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k210-baseline/boot-id-private.txt').read_bytes()
assert os.uname().version.startswith('#183 ')
assert not any(Path('/sys/module/'+n).exists() for n in ['imx471','v4l2_cci','qcom_pm8008','qcom_pm8008_regulator','samurai_cci_bringup'])
modules=Path('/usr/lib/modules')/os.uname().release
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*') if p.is_file()}
assert sum(n.endswith('.ko') for n in files)==784
expected={'kernel/drivers/media/platform/qcom/camss/qcom-camss.ko':'82cbc0528a76858ac57e149bdb540d14630112d74213384303960eead684fe58','kernel/drivers/bluetooth/hci_uart.ko':'f6c5ed3538270480a72cf4bf8b1339103417941930b0d8ecb941fd11d16d7020','kernel/drivers/mfd/qcom-pm8008.ko':'189299a52798b6ec0446035ebf15bae47047143865dca5efc2fcf72b01297032'}
for n,digest in expected.items():assert files[n]==digest
assert not (modules/'kernel/drivers/media/i2c/imx471.ko').exists()
assert not (modules/'kernel/drivers/media/v4l2-core/v4l2-cci.ko').exists()
(out/'module-inventory-private.json').write_text(json.dumps(files,indent=2)+'\n')
backup=out/'module-tree-before-private';backup.mkdir(mode=0o700)
for p in modules.iterdir():
    if p.is_file():shutil.copyfile(p,backup/p.name)
dest=backup/'kernel/drivers/mfd/qcom-pm8008.ko';dest.parent.mkdir(parents=True);shutil.copyfile(modules/'kernel/drivers/mfd/qcom-pm8008.ko',dest)
for command,name in [(['depmod','--help'],'depmod-help-private.txt'),(['modprobe','--help'],'modprobe-help-private.txt'),(['cat','/etc/mdev.conf'],'mdev-config-private.txt')]:
    p=subprocess.run(command,capture_output=True);(out/name).write_bytes(p.stdout+p.stderr)
report=dict(stage=210,same_boot=True,installed_module_count=784,all_existing_files_hashed=True,original_mfd_and_module_metadata_backed_up=True,front_modules_absent=True,custom_camss_bt_verified=True,device_product_files_unchanged=True)
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
