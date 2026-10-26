from pathlib import Path
import hashlib,json,os,re,subprocess
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k197-tpg-control';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k197-baseline/boot-id-private.txt').read_bytes();assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512';assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_front_overlay','imx471','i2c_qcom_cci'])
for process in Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  for p in (process/'fd').iterdir():
   try:target=os.readlink(p)
   except OSError:continue
   assert not target.startswith(('/dev/video','/dev/v4l-subdev','/dev/media'))
 except (FileNotFoundError,PermissionError):pass
tool=root/'k197-offline-tools/tpg-control-aarch64-private';meta=json.loads((root/'k197-offline-tools/tpg-control-build-validation.json').read_text());assert hashlib.sha256(tool.read_bytes()).hexdigest()==meta['binary_sha256'];tool.chmod(0o700);before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before);old=subprocess.check_output(['media-ctl','-p']);(out/'topology-before-private.txt').write_bytes(old);p=subprocess.run([str(tool),'--capture',str(out/'first-frame-private.raw')],capture_output=True,timeout=35);(out/'capture-private.log').write_bytes(p.stdout+p.stderr);after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);new=subprocess.check_output(['media-ctl','-p']);(out/'topology-after-private.txt').write_bytes(new)
r=dict(stage=197,capture_returncode=p.returncode,physical_sensor_not_present=True,frames_are_internal_tpg_only=True,topology_restored=old==new,fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()));(out/'summary.json').write_text(json.dumps(r,indent=2)+'\n');assert r['topology_restored'] and all(v==0 for v in r['fault_delta'].values()) and r['taint']==512;print(json.dumps(r));print(re.sub(r'hash=[0-9a-f]+','hash=<private>',(p.stdout+p.stderr).decode())[-3000:]);print(after[len(before):].decode(errors='replace')[-3000:])
