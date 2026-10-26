"""Compare sensor-first removal after the captured provider-first clock WARN."""
from pathlib import Path
import ast,ctypes,fcntl,hashlib,json,os,struct,subprocess,time
os.umask(0o077);root=Path('/var/lib/samurai');out=root/'k211-remove-order-test';out.mkdir(mode=0o700)
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
names=['qcom_camss','imx471','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci']
assert all(not Path('/sys/module'/Path(n)).exists() for n in names)
before=subprocess.check_output(['dmesg']);assert before.count(b'WARNING:')==1 and b'cam_cc_mclk2_clk status stuck' in before
assert Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
assert not subprocess.run(['pgrep','-u','10000'],stdout=subprocess.DEVNULL).returncode==0
assert not Path('/run/k211-bootloader-state').exists()
ifd=os.open('/dev/i2c-1',os.O_RDWR|os.O_CLOEXEC)
source=ast.parse((root/'k195-modules/probe-q-reset-address.py').read_text());functions=[n for n in source.body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in ['Msg','Rdwr','read','snapshot']]
assert len(functions)==4;exec(compile(ast.Module(body=functions,type_ignores=[]),'known-pmic-read-only','exec'))
pmic=snapshot(4);assert pmic['identity']['data']==[0,0,0,1,0x51,0x2c] and all(x['enable']['data']==[0] for x in pmic['ldos']);os.close(ifd)
(out/'pmic-before-private.json').write_text(json.dumps(pmic,indent=2)+'\n')
report=dict(stage=211,source_boot_guard_passed=True,known_provider_first_warning_count=1,initial_taint=512,pmic_outputs_off_before=True,commands=[],new_warnings=0,phase='load-normal-drivers')
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def command(args):
    p=subprocess.run(args,capture_output=True,timeout=20);report['commands'].append(dict(command=args[0],module=args[-1],exit=p.returncode));(out/('command-'+str(len(report['commands']))+'-private.log')).write_bytes(p.stdout+p.stderr)
    log=subprocess.check_output(['dmesg']);(out/('dmesg-'+str(len(report['commands']))+'-private.txt')).write_bytes(log);report['new_warnings']=log.count(b'WARNING:')-before.count(b'WARNING:');save();assert p.returncode==0 and report['new_warnings']==0
save()
for name in ['qcom_pm8008','qcom_camss','i2c_qcom_cci','imx471']:command(['modprobe',name])
sensor=Path('/sys/bus/i2c/devices/7-0010')
for _ in range(40):
    if (sensor/'driver').exists() and all(Path('/sys/module'/Path(n)).exists() for n in names):break
    time.sleep(.1)
assert (sensor/'driver').resolve().name=='imx471';report['new_sensor_bound']=True
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1
fd=os.open('/dev/'+nodes[0].name,os.O_RDWR|os.O_CLOEXEC)
try:
    buf=bytearray(64);struct.pack_into('4I',buf,0,1,0,0,0);fcntl.ioctl(fd,0xc040563d,buf,True);report['active_crop']=list(struct.unpack_from('4i',buf,16));assert report['active_crop']==[8,408,4640,2644]
finally:os.close(fd)
time.sleep(1)
for p in [sensor,Path('/sys/bus/platform/devices/acb3000.camss'),Path('/sys/bus/platform/devices/ac4b000.cci')]:assert (p/'power/runtime_status').read_text().strip()=='suspended'
(out/'before-remove-genpd-private.txt').write_bytes(Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_bytes())
report['phase']='remove-sensor-before-camss';save()
for name in ['imx471','qcom_camss','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci']:command(['rmmod',name])
assert all(not Path('/sys/module'/Path(n)).exists() for n in names)
report.update(phase='complete',all_six_unloaded=True,sensor_first_removal_without_new_warning=True,final_taint=int(Path('/proc/sys/kernel/tainted').read_text()))
save();print(json.dumps(report))
