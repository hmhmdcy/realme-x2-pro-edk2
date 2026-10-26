"""Exercise normal PM8008 MFD probe from the already-assigned address."""
from pathlib import Path
import hashlib,json,subprocess
stage=Path('/var/lib/samurai/k194-modules')
prefix=(stage/'probe-q-reset-address.py').read_text().split('report=dict(',1)[0]
assert "out=root/'k194-q-reset'" in prefix
exec(compile(prefix.replace("out=root/'k194-q-reset'","out=root/'k194-pmic-warmprobe'"),'<verified-i2c-gpio-prefix>','exec'))
assert not any(Path('/sys/module/'+n).exists() for n in ['samurai_pmic_fixture','qcom_pm8008','qcom_pm8008_regulator'])
report=dict(stage=194,before=snapshot(4),gpio1_before=sample(0),gpio4_before=sample(3),attempts=[],reset_levels=[],writes=[])
assert report['gpio1_before']==0 and report['gpio4_before']==1 and report['before']['identity']['data']==[0,0,0,1,0x51,0x2c] and report['before']['sid']['data']==[1]
assert all(x['enable']['data']==[0] for x in report['before']['ldos']) and not read(8,0x100,6)['success']
fixture=json.loads((stage/'pmic-fixture-build-validation.json').read_text());driver=json.loads((stage/'pmic-module-build-validation.json').read_text())
assert hashlib.sha256((stage/'samurai-pmic-fixture.ko').read_bytes()).hexdigest()==fixture['module_sha256'] and hashlib.sha256((stage/'qcom-pm8008.ko').read_bytes()).hexdigest()==driver['module_sha256']
before_log=subprocess.check_output(['dmesg']);(out/'dmesg-before-private.txt').write_bytes(before_log)
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def set_level(value):
 b=bytearray(struct.pack('QQ',value,1));fcntl.ioctl(line,0xc010b40f,b,True);assert level(line)==value;report['reset_levels'].append(value);save()
def run(args):
 p=subprocess.run(args,capture_output=True,timeout=20);report['attempts'].append(dict(command=args[0],module=args[-1].split('/')[-1],returncode=p.returncode));(out/('command-'+str(len(report['attempts']))+'-private.log')).write_bytes(p.stdout+p.stderr);save();return p
def interrupt(signum,frame):raise RuntimeError('Interrupted; restore known PMIC state')
for sig in [signal.SIGTERM,signal.SIGINT,signal.SIGHUP]:signal.signal(sig,interrupt)
save()
try:
 assert run(['insmod',str(stage/'qcom-pm8008.ko')]).returncode==0
 report['reset_address4']=read(4,0x100,6);report['reset_address8']=read(8,0x100,6);save()
 assert run(['insmod',str(stage/'samurai-pmic-fixture.ko')]).returncode==0
 assert Path('/sys/module/samurai_pmic_fixture').exists()
 primary=Path('/sys/bus/i2c/devices/1-0004');secondary=Path('/sys/bus/i2c/devices/1-0005')
 assert (primary/'driver').resolve().name=='pm8008' and secondary.exists()
 report['bound_driver']=(primary/'driver').resolve().name;report['during_probe']=snapshot(4);report['address8_during']=read(8,0x100,6)
 report['regulator_child_loaded']=Path('/sys/module/qcom_pm8008_regulator').exists()
 report['regulators_during']=[dict(name=(p/'name').read_text().strip(),node=str((p/'device').resolve()).split('/1-0004')[-1]) for p in Path('/sys/class/regulator').glob('regulator.*') if '1-0004' in str(p.resolve())]
 report['gpio1_during']=sample(0);save()
 assert report['during_probe']==report['before'] and not report['address8_during']['success'] and report['gpio1_during']==0
finally:
 if Path('/sys/module/samurai_pmic_fixture').exists():assert run(['rmmod','samurai_pmic_fixture']).returncode==0
 assert not Path('/sys/bus/i2c/devices/1-0004').exists() and not Path('/sys/bus/i2c/devices/1-0005').exists()
 if Path('/sys/module/qcom_pm8008').exists():assert run(['rmmod','qcom_pm8008']).returncode==0
 if Path('/sys/module/qcom_pm8008_regulator').exists():assert run(['rmmod','qcom_pm8008_regulator']).returncode==0
 if line is not None:
  if level(line)!=1:set_level(1);time.sleep(.010)
  os.close(line);line=None
 at4=read(4,0x100,6);at8=read(8,0x100,6);report['cleanup_initial_addresses']=dict(at4=at4,at8=at8);save()
 if not at4['success'] and at8.get('data')==report['before']['identity']['data']:
  report['writes'].append(write(8,0x644,[1]));save();time.sleep(.010)
 report['after_restore']=snapshot(4);report['address8_after']=read(8,0x100,6);report['gpio1_after']=sample(0);report['gpio4_after']=sample(3);os.close(gfd);os.close(ifd);save()
after_log=subprocess.check_output(['dmesg']);(out/'dmesg-after-private.txt').write_bytes(after_log)
report['fault_delta']={k:after_log.count(v)-before_log.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',slpi_fatal=b'fatal error received',bluetooth=b'Frame reassembly failed').items()};report['taint']=int(Path('/proc/sys/kernel/tainted').read_text());save()
assert report['after_restore']==report['before'] and not report['address8_after']['success'] and report['gpio1_after']==0 and report['gpio4_after']==1 and report['taint']==512 and all(v==0 for v in report['fault_delta'].values())
assert b'assigned PM8008 primary address 0x04' not in after_log[len(before_log):] and not report['writes'] and not report['reset_levels']
print(json.dumps(dict(stage=194,normal_mfd_driver_bound=True,already_assigned_address=4,reset_pulse_needed=False,driver_module_sha256=driver['module_sha256'],fixture_module_sha256=fixture['module_sha256'],seven_ldo_sample_unchanged=True,all_diagnostic_modules_unloaded=True,gpio_levels_restored=True,sid_reassignment_needed=False,regulator_child_loaded=report['regulator_child_loaded'],fault_delta=report['fault_delta'],taint=report['taint'],full_phone_cold_boot_tested=False)))
