from pathlib import Path
import hashlib,json,os,re,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k199-mmcx-tpg';out.mkdir(mode=0o700);assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k199-baseline/boot-id-private.txt').read_bytes();assert os.uname().version.startswith('#183 ') and Path('/proc/sys/kernel/tainted').read_text().strip()=='512';assert all(not Path('/sys/module/'+n).exists() for n in ['samurai_camera_perf','samurai_front_overlay','imx471','i2c_qcom_cci'])
for process in Path('/proc').iterdir():
 if not process.name.isdigit():continue
 try:
  for p in (process/'fd').iterdir():
   try:target=os.readlink(p)
   except OSError:continue
   assert not target.startswith(('/dev/video','/dev/media','/dev/v4l-subdev'))
 except (FileNotFoundError,PermissionError):pass
original=Path(subprocess.check_output(['modinfo','-n','qcom-camss'],text=True).strip());assert hashlib.sha256(original.read_bytes()).hexdigest()=='e9b73f4c6bad90fbd6ff89ba45894c88b32b51bc9836ddd741ff56876eb13b0d';helper=root/'k199-modules/samurai-camera-perf.ko';meta=json.loads((root/'k199-modules/perf-helper-build-validation.json').read_text());assert hashlib.sha256(helper.read_bytes()).hexdigest()==meta['module_sha256'];tool=root/'k197-offline-tools/tpg-control-aarch64-private';assert hashlib.sha256(tool.read_bytes()).hexdigest()=='768705482162ad0056a8a949f4a95f6b922432dd2676ec54beaf0d8433a0c759'
before=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before);old_graph=subprocess.check_output(['media-ctl','-p']);(out/'graph-before-private.txt').write_bytes(old_graph);report=dict(stage=199,attempts=[])
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def command(args):
 p=subprocess.run(args,capture_output=True,timeout=20);report['attempts'].append(dict(action=args[0],returncode=p.returncode));(out/('command-'+str(len(report['attempts']))+'-private.log')).write_bytes(p.stdout+p.stderr);save();return p
def snapshot(label):
 for name,path in [('genpd','/sys/kernel/debug/pm_genpd/pm_genpd_summary'),('clocks','/sys/kernel/debug/clk/clk_summary'),('interrupts','/proc/interrupts')]:
  if Path(path).exists():(out/(label+'-'+name+'-private.txt')).write_bytes(Path(path).read_bytes())
snapshot('before')
try:
 p=command(['insmod',str(helper)]);assert p.returncode!=0 and not Path('/sys/module/samurai_camera_perf').exists();report['default_off_guard_passed']=True;save()
 assert command(['insmod',str(helper),'enable=1']).returncode==0;assert Path('/sys/module/samurai_camera_perf/parameters/active').read_text().strip()=='Y' and Path('/sys/module/samurai_camera_perf/parameters/requested_level').read_text().strip()=='384';snapshot('performance-active');report['own_consumer_level']=384;save()
 p=subprocess.run([str(tool),'--capture',str(out/'first-tpg-frame-private.raw')],capture_output=True,timeout=35);(out/'capture-private.log').write_bytes(p.stdout+p.stderr);report['capture_returncode']=p.returncode;report['tpg_frames']=len(re.findall(rb'^FRAME ',p.stdout,re.M));snapshot('after-capture');save()
finally:
 if Path('/sys/module/samurai_camera_perf').exists():assert command(['rmmod','samurai_camera_perf']).returncode==0
 snapshot('restored');report['helper_unloaded']=not Path('/sys/module/samurai_camera_perf').exists();save()
after=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after);new_graph=subprocess.check_output(['media-ctl','-p']);(out/'graph-after-private.txt').write_bytes(new_graph);report.update(topology_restored=old_graph==new_graph,fault_delta={k:after.count(v)-before.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()},taint=int(Path('/proc/sys/kernel/tainted').read_text()));save();assert report['topology_restored'] and all(v==0 for v in report['fault_delta'].values()) and report['taint']==512
print(json.dumps(report));print(re.sub(r'hash=[0-9a-f]+','hash=<private>',(p.stdout+p.stderr).decode())[-3000:]);print(after[len(before):].decode(errors='replace')[-3500:])
