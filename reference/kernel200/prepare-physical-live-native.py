from pathlib import Path
import hashlib,json,os,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k200-live-prepare-r3';out.mkdir(mode=0o700);stage=root/'k200-modules'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k200-camera-baseline/boot-id-private.txt').read_bytes();assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
for r in json.loads((stage/'manifest.json').read_text()):assert hashlib.sha256((stage/r['file']).read_bytes()).hexdigest()==r['sha256']
assert not Path('/sys/module/i2c_qcom_cci').exists() and not Path('/sys/module/imx471').exists() and not Path('/lib/firmware/samurai/k196-front.dtbo').exists()
assert all(g['ctl']==1 and g['level']==0 for g in json.loads((root/'k200-front-session/before-private.json').read_text())['gpios'])
loaded=[];attempts=[]
vio_node=Path('/sys/firmware/devicetree/base/soc@0/rsc@18200000/regulators-1/ldo1')
def vio_state():
 regs=[p for p in Path('/sys/class/regulator').glob('regulator.*') if (p/'of_node').exists() and (p/'of_node').resolve()==vio_node]
 assert len(regs)==1
 return {n:(regs[0]/n).read_text().strip() for n in ['state','microvolts','num_users']}
vio_before=vio_state();assert vio_before==dict(state='disabled',microvolts='1800000',num_users='0')
def command(args):
 p=subprocess.run(args,capture_output=True,timeout=20);attempts.append(dict(command=args[0],module=args[-1].split('/')[-1],returncode=p.returncode));(out/('command-'+str(len(attempts))+'-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
try:
 command(['modprobe','i2c-qcom-cci']);loaded.append('i2c_qcom_cci')
 for file,name in [('samurai-cci-bringup-k193-private.ko','samurai_cci_bringup'),('samurai-vio-phandle.ko','samurai_vio_phandle'),('qcom-pm8008.ko','qcom_pm8008'),('v4l2-cci.ko','v4l2_cci')]:
  command(['insmod',str(stage/file)]);assert Path('/sys/module/'+name).exists();loaded.append(name)
 time.sleep(2)
 assert vio_state()==vio_before and int(Path('/sys/module/samurai_vio_phandle/parameters/supply_enable_state').read_text())==0
 (out/'vio-read-only-lookup.json').write_text(json.dumps(dict(before=vio_before,after=vio_state(),enable_state=0,no_power_state_write=True),indent=2)+'\n')
 data=json.loads((root/'k200-camera-baseline/resources.json').read_text());data['vio_phandle']=int(Path('/sys/module/samurai_vio_phandle/parameters/assigned_handle').read_text());data['loaded_modules']=loaded;data['controller_runtime_status']=Path('/sys/bus/platform/devices/ac4b000.cci/power/runtime_status').read_text().strip();assert Path('/sys/bus/i2c/devices/i2c-7').exists() and not Path('/sys/bus/i2c/devices/7-0010').exists()
 (out/'live-input.json').write_text(json.dumps(data,indent=2)+'\n');(out/'attempts.json').write_text(json.dumps(attempts,indent=2)+'\n');print(json.dumps(dict(stage=200,vio_phandle=data['vio_phandle'],controller_runtime_status=data['controller_runtime_status'],resources_ready=True,sensor_not_created=True)))
except BaseException:
 for n in reversed(loaded):subprocess.run(['rmmod',n],capture_output=True,timeout=15)
 (out/'attempts.json').write_text(json.dumps(attempts,indent=2)+'\n');raise
