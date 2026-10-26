from pathlib import Path
import fcntl,json,os,struct,subprocess,time
root=Path('/var/lib/samurai');out=root/'k211-remove-order-test'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(root/'k211-before-reboot/boot-id-private.txt').read_bytes()
report=json.loads((out/'summary.json').read_text());assert report['phase']=='load-normal-drivers' and len(report['commands'])==4 and report['new_warnings']==0
before=subprocess.check_output(['dmesg']);assert before.count(b'WARNING:')==1 and Path('/proc/sys/kernel/tainted').read_text().strip()=='512'
names=['imx471','qcom_camss','v4l2_cci','qcom_pm8008_regulator','qcom_pm8008','i2c_qcom_cci'];assert all(Path('/sys/module'/Path(n)).exists() for n in names)
def save():(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
def states():return {n:Path(p,'power/runtime_status').read_text().strip() for n,p in dict(sensor='/sys/bus/i2c/devices/7-0010',camss='/sys/bus/platform/devices/acb3000.camss',cci='/sys/bus/platform/devices/ac4b000.cci').items()}
report['pm_before_enumeration']=states();save()
p=subprocess.run(['cam','--list'],capture_output=True,timeout=30);(out/'new-driver-cam-list-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
report['new_driver_crop_error_absent']=b'Failed to retrieve the sensor crop rectangle' not in p.stderr
report['heap_allocator_error_absent']=b'Could not open any dma-buf provider' not in p.stderr
fd=os.open('/dev/video0',os.O_RDWR|os.O_NONBLOCK|os.O_CLOEXEC);os.close(fd)
time.sleep(2);report['pm_after_enumeration_and_video_open_close']=states();save()
assert all(x=='suspended' for x in report['pm_after_enumeration_and_video_open_close'].values())
nodes=[p for p in Path('/sys/class/video4linux').glob('v4l-subdev*') if (p/'name').read_text().strip()=='imx471 7-0010'];assert len(nodes)==1
fd=os.open('/dev/'+nodes[0].name,os.O_RDWR|os.O_CLOEXEC)
try:
    buf=bytearray(64);struct.pack_into('4I',buf,0,1,0,0,0);fcntl.ioctl(fd,0xc040563d,buf,True);report['active_crop']=list(struct.unpack_from('4i',buf,16));assert report['active_crop']==[8,408,4640,2644]
finally:os.close(fd)
(out/'before-remove-genpd-private.txt').write_bytes(Path('/sys/kernel/debug/pm_genpd/pm_genpd_summary').read_bytes())
report['phase']='remove-sensor-before-camss';save()
for name in names:
    p=subprocess.run(['rmmod',name],capture_output=True,timeout=20);report['commands'].append(dict(command='rmmod',module=name,exit=p.returncode));(out/('command-'+str(len(report['commands']))+'-private.log')).write_bytes(p.stdout+p.stderr)
    log=subprocess.check_output(['dmesg']);(out/('dmesg-'+str(len(report['commands']))+'-private.txt')).write_bytes(log);report['new_warnings']=log.count(b'WARNING:')-before.count(b'WARNING:');save();assert p.returncode==0 and report['new_warnings']==0
assert all(not Path('/sys/module'/Path(n)).exists() for n in names)
report.update(phase='complete',all_six_unloaded=True,sensor_first_removal_without_new_warning=True,first_idle_guard_failed_after_reprobe_until_standard_video_open_close=True,final_taint=int(Path('/proc/sys/kernel/tainted').read_text()));save();print(json.dumps(report))
