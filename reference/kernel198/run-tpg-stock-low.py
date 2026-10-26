from pathlib import Path
import hashlib,json,os,re,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k198-tpg-stock-low';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k198-baseline/boot-id-private.txt').read_bytes();assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512';assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_front_overlay','imx471','i2c_qcom_cci'])
for process in Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  for p in (process/'fd').iterdir():
   try:target=os.readlink(p)
   except OSError:continue
   assert not target.startswith(('/dev/video','/dev/v4l-subdev','/dev/media'))
 except (FileNotFoundError,PermissionError):pass
original=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip());original_hash=hashlib.sha256(original.read_bytes()).hexdigest();candidate=root/'k198-modules/qcom-camss-stock-low.ko';meta=json.loads((root/'k198-modules/stock-low-module-build-validation.json').read_text());assert hashlib.sha256(candidate.read_bytes()).hexdigest()==meta['module_sha256'];before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before);old=subprocess.check_output(['media-ctl','-p']);removed=False;loaded=False
try:
 subprocess.run(['rmmod','qcom_camss'],check=True,capture_output=True,timeout=15);removed=True;subprocess.run(['insmod',str(candidate),'clock_trace=1'],check=True,capture_output=True,timeout=15);loaded=True
 tool=root/'k197-offline-tools/tpg-control-aarch64-private';p=subprocess.run([str(tool),'--capture',str(out/'first-frame-private.raw')],capture_output=True,timeout=35);(out/'capture-private.log').write_bytes(p.stdout+p.stderr)
finally:
 if loaded:subprocess.run(['rmmod','qcom_camss'],check=True,capture_output=True,timeout=15)
 if removed:assert hashlib.sha256(original.read_bytes()).hexdigest()==original_hash;subprocess.run(['modprobe','qcom-camss'],check=True,capture_output=True,timeout=15)
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);new=subprocess.check_output(['media-ctl','-p']);(out/'topology-restored-private.txt').write_bytes(new)
r=dict(stage=198,candidate_module_sha256=meta['module_sha256'],original_module_sha256=original_hash,capture_returncode=p.returncode,physical_sensor_not_present=True,internal_tpg_only=True,original_module_restored=True,topology_restored=old==new,fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()));(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');assert r['topology_restored'] and all(v==0 for v in r['fault_delta'].values()) and r['taint']==512;print(json.dumps(r));print(re.sub(r'hash=[0-9a-f]+','hash=<private>',(p.stdout+p.stderr).decode())[-3000:]);print(after[len(before):].decode(errors='replace')[-16000:])
