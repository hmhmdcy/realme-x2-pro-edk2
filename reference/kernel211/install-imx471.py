from pathlib import Path
import fcntl,hashlib,json,os,shutil,struct,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-module-install';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
modules=Path('/usr/lib/modules')/os.uname().release;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before=json.loads((root/'k211-module-before/module-inventory-before-private.json').read_text())
assert before=={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*') if p.is_file()}
stage=root/'k211-module-stage';proof=json.loads((stage/'imx471-module-build-validation.json').read_text());new=stage/'imx471.ko';assert sha(new)==proof['module_sha256']
name='kernel/drivers/media/i2c/imx471.ko';target=modules/name
temporary=target.with_name(target.name+'.k211-new');assert not temporary.exists();shutil.copyfile(new,temporary);temporary.chmod(0o644);os.replace(temporary,target)
p=subprocess.run(['depmod','-a'],capture_output=True,timeout=60);(out/'depmod-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
assert subprocess.check_output(['modinfo','-F','vermagic','imx471'],text=True).strip()==proof['vermagic']
after={str(p.relative_to(modules)):sha(p) for p in modules.rglob('*') if p.is_file()}
assert set(after)==set(before) and len(after)==786
assert {n for n in after if n.endswith('.ko') and before[n]!=after[n]}=={name}
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1
fd=os.open('/dev/'+nodes[0].name,os.O_RDWR|os.O_CLOEXEC)
try:
    buf=bytearray(64);struct.pack_into('4I',buf,0,1,0,0,0)
    try:fcntl.ioctl(fd,0xc040563d,buf,True)
    except OSError as error:assert error.errno==22
    else:raise AssertionError('Running driver unexpectedly changed without transition')
finally:os.close(fd)
assert Path('/sys/bus/i2c/devices/7-0010/power/runtime_status').read_text().strip()=='suspended'
(out/'module-inventory-after-private.json').write_text(json.dumps(after,indent=2)+'\n')
(out/'module-tree.sha256').write_text(''.join(digest+'  '+name+'\n' for name,digest in sorted(after.items())))
report=dict(stage=211,updated_sensor_module_installed=True,installed_sensor_module_sha256=sha(target),only_sensor_module_path_changed=True,all_771_other_modules_preserved=True,total_modules=772,total_regular_files=786,running_old_driver_unchanged_crop_still_einval=True,compatible_metadata_regenerated=True,new_module_probe_requires_planned_reboot=True,sensor_suspended=True,taint=int(Path('/proc/sys/kernel/tainted').read_text()))
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
