from pathlib import Path
import hashlib,json,os,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k193-cci-load';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k193-baseline/boot-id-private.txt').read_bytes()
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
node=Path('/sys/firmware/devicetree/base/soc@0/cci@ac4b000');assert (node/'status').read_bytes()==b'disabled\0' and not Path('/sys/bus/platform/devices/ac4b000.cci').exists()
tools=root/'k193-tools';info=json.loads((tools/'cci-helper-build-validation.json').read_text());candidate=tools/'samurai-cci-bringup-k193-private.ko';assert hashlib.sha256(candidate.read_bytes()).hexdigest()==info['candidate_sha256']
assert hashlib.sha256((tools/'samurai-cci-bringup.c').read_bytes()).hexdigest()==info['helper_source_sha256']
assert os.uname().version.startswith('#183 ') and os.uname().release in info['vermagic']
before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log)
report=dict(stage=193,cci_driver_preloaded=Path('/sys/module/i2c_qcom_cci').exists(),helper_sha256=info['candidate_sha256'])
(out/'precondition-private.json').write_text(json.dumps(report,indent=2))
loaded=subprocess.run(['modprobe','i2c-qcom-cci'],capture_output=True,timeout=15);(out/'cci-driver-load-private.log').write_bytes(loaded.stdout+loaded.stderr);assert loaded.returncode==0
driver=Path(subprocess.check_output(['modinfo','-n','i2c-qcom-cci'],text=True).strip());report['cci_driver_sha256']=hashlib.sha256(driver.read_bytes()).hexdigest()
with (out/'insmod-private.log').open('xb') as log:
 proc=subprocess.Popen(['insmod',str(candidate)],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
 (out/'loader-pid-private.txt').write_text(str(proc.pid))
 try:proc.wait(timeout=15)
 except subprocess.TimeoutExpired:
  (out/'loader-still-running.txt').write_text('Observe the saved live PID; do not reload\n');print(json.dumps(dict(stage=193,loader_running=True)));raise SystemExit(0)
report['insmod_exit']=proc.returncode
after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log)
report['cci_status']=(node/'status').read_bytes().rstrip(b'\0').decode();report['helper_loaded']=Path('/sys/module/samurai_cci_bringup').exists();report['taint']=int(Path('/proc/sys/kernel/tainted').read_text())
pdev=Path('/sys/bus/platform/devices/ac4b000.cci');report['cci_driver_bound']=(pdev/'driver').exists()
adapters=[]
for p in Path('/sys/bus/i2c/devices').glob('i2c-*'):
 of=p/'of_node'
 if of.exists() and '/cci@ac4b000/' in str(of.resolve()):
  adapters.append(dict(adapter=p.name,name=(p/'name').read_text().strip(),of_path=str(of.resolve()),master=int.from_bytes((of/'reg').read_bytes(),'big')))
report['cci_adapters']=adapters
before=before_log.decode();after=after_log.decode();report['fault_delta']={k:after.count(v)-before.count(v) for k,v in dict(warning='WARNING:',oops='Oops:',gpu='gpu fault:',slpi_fatal='fatal error received',bluetooth='Frame reassembly failed').items()}
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
assert proc.returncode==0 and report['helper_loaded'] and report['cci_driver_bound'] and sorted(x['master'] for x in adapters)==[0,1]
assert report['taint']==0 and all(v==0 for v in report['fault_delta'].values())
