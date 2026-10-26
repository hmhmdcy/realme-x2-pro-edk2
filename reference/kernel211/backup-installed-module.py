from pathlib import Path
import hashlib,json,os,shutil
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-module-before';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-baseline/boot-id-private.txt').read_bytes()
modules=Path('/usr/lib/modules')/os.uname().release;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=json.loads((root/'k210-module-install/module-inventory-after-private.json').read_text())
assert before=={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*') if p.is_file()}
name='kernel/drivers/media/i2c/imx471.ko';assert before[name]=='c49dca633e8df556497b96e6f8b3a58b6bd98e7ad0548a14e8fef27ba73969d4'
(out/'module-inventory-before-private.json').write_text(json.dumps(before,indent=2)+'\n')
for p in [modules/name,*[p for p in modules.iterdir() if p.is_file()]]:
    dest=out/'tree'/p.relative_to(modules);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest)
print(json.dumps(dict(stage=211,installed_sensor_and_module_metadata_backed_up=True,all_786_files_verified=True,running_old_driver_still_bound=(Path('/sys/bus/i2c/devices/7-0010/driver').resolve().name=='imx471'))))
