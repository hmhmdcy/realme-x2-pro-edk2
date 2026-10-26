"""Read actual common-driver bindings, metadata and idle power after the new DTB."""
from pathlib import Path
import json
import sys
import host

R=Path(__file__).resolve().parent
build=json.loads((R/'module-build-validation.json').read_text())
code=r'''
from pathlib import Path
import fcntl,hashlib,json,os,struct,subprocess
r=Path('/var/lib/samurai');assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==(r/'k267-work/boot-id-private.txt').read_bytes()
report=dict(stage=267,modules={},pmics={},sensors={},rails={},taint=int(Path('/proc/sys/kernel/tainted').read_text()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def note(p):
 data=p.read_bytes();offset=struct.unpack_from('<Q',data,40)[0];size,count,index=struct.unpack_from('<HHH',data,58)
 sec=[struct.unpack_from('<IIQQQQIIQQ',data,offset+i*size) for i in range(count)]
 strings=data[sec[index][4]:sec[index][4]+sec[index][5]]
 return next(data[s[4]:s[4]+s[5]] for s in sec if strings[s[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id')
for name in ['qcom_pm8008','qcom_pm8008_regulator','imx319','imx471','qcom_camss']:
 p=Path('/sys/module',name)
 if not p.exists():report['modules'][name]=dict(loaded=False);continue
 file=Path(subprocess.check_output(['modinfo','-n',name],text=True).strip())
 report['modules'][name]=dict(loaded=True,sha256=sha(file),loaded_note_matches_disk=note(file)==(p/'notes/.note.gnu.build-id').read_bytes(),
  intree=subprocess.check_output(['modinfo','-F','intree',str(file)],text=True).strip(),
  parameters={x.name:x.read_text().strip() for x in (p/'parameters').glob('*') if x.is_file()})
for n in ['1-0004','1-0008']:
 p=Path('/sys/bus/i2c/devices',n)
 report['pmics'][n]=dict(bound=(p/'driver').exists(),driver=(p/'driver').resolve().name if (p/'driver').exists() else None,
  children=[dict(name=x.name,driver=(x/'driver').resolve().name if (x/'driver').exists() else None) for x in p.glob('pm8008-regulator.*')],
  supplier_links=[x.name for x in p.glob('supplier:*')])
for n in Path('/sys/class/video4linux').glob('v4l-subdev*'):
 entity=(n/'name').read_text().strip()
 if not entity.startswith(('imx319 ','imx471 ')):continue
 dev=(n/'device').resolve();of=(dev/'of_node').resolve();selection={}
 fd=os.open('/dev/'+n.name,os.O_RDWR|os.O_CLOEXEC)
 try:
  for label,target in [('crop',0),('default',1),('bounds',2),('native',3)]:
   data=bytearray(64);struct.pack_into('IIII',data,0,1,0,target,0)
   try:fcntl.ioctl(fd,0xc040563d,data,True);selection[label]=dict(zip(['left','top','width','height'],struct.unpack_from('iiII',data,16)))
   except OSError as e:selection[label]=dict(errno=e.errno)
 finally:os.close(fd)
 report['sensors'][entity.split()[0]]=dict(entity=entity,node='/dev/'+n.name,sysfs_device=str(dev),
  compatible=(of/'compatible').read_bytes().decode().rstrip('\0'),runtime=(dev/'power/runtime_status').read_text().strip(),
  properties={x:int.from_bytes((of/x).read_bytes(),'big') for x in ['orientation','rotation'] if (of/x).exists()},selection=selection,
  controls=subprocess.check_output(['v4l2-ctl','-d','/dev/'+n.name,'--list-ctrls'],text=True),
  supplier_links=[x.name for x in dev.glob('supplier:*')])
for p in Path('/sys/class/regulator').glob('regulator.*'):
 name=(p/'name').read_text().strip()
 if name.startswith(('cam-front-','cam-rear-')):
  report['rails'][name]={k:(p/k).read_text().strip() for k in ['state','num_users','microvolts'] if (p/k).exists()}
report['lab_modules_absent']=not any(Path('/sys/module',n).exists() for n in ['qcom_pm8008_imx319_lab','reset_realme_rmx1931_pm8008'])
report['old_lab_config_absent']=not Path('/etc/modprobe.d/samurai-pmic-bringup.conf').exists()
report['old_reset_dt_node_absent']=not Path('/sys/firmware/devicetree/base/camera-pmic-resets').exists()
report['regulator_summary']=Path('/sys/kernel/debug/regulator/regulator_summary').read_text()
report['dmesg']=subprocess.check_output(['dmesg'],text=True)
report['clock_summary']=Path('/sys/kernel/debug/clk/clk_summary').read_text()
report['cam_help']=subprocess.run(['cam','-l'],capture_output=True,text=True,timeout=20).stdout
for n,digest in json.loads((r/'k265-package-transaction/summary.json').read_text())['payload_sha256'].items():assert sha(Path('/')/n)==digest
print(json.dumps(report))
'''
audit=sys.argv[1:]==['--audit-existing'];assert not sys.argv[1:] or audit
if audit:d=json.loads((host.PRIVATE/'postboot-hardware-private.json').read_text())
else:
    q=host.ssh('python3 -',input=code.encode(),timeout=35)
    (host.PRIVATE/'postboot-hardware-private.json').write_bytes(q.stdout)
    d=json.loads(q.stdout)
for key in ['dmesg','clock_summary','regulator_summary']:(host.PRIVATE/(key+'-postboot-private.txt')).write_text(d[key])
expected={'qcom_pm8008':'qcom-pm8008.ko','qcom_pm8008_regulator':'qcom-pm8008-regulator.ko','imx319':'imx319.ko'}
for name,file in expected.items():
 row=d['modules'][name];assert row['loaded'] and row['loaded_note_matches_disk'] and row['sha256']==build['modules'][file]['sha256']
assert d['taint']==0 and d['lab_modules_absent'] and d['old_lab_config_absent'] and d['old_reset_dt_node_absent']
assert set(d['sensors'])=={'imx319','imx471'}
assert d['sensors']['imx319']['properties']=={'orientation':1}
assert d['sensors']['imx319']['selection']['crop']==dict(left=0,top=8,width=3280,height=2448)
assert all(x['bound'] and x['driver']=='pm8008' for x in d['pmics'].values())
assert any('1-0004' in x for x in d['pmics']['1-0008']['supplier_links'])
assert all(row['state']=='disabled' and row['num_users']=='0' for row in d['rails'].values())
report={k:v for k,v in d.items() if k not in ['dmesg','clock_summary','regulator_summary','cam_help']}
report.update(standard_cam_enumerated_both=all(x in d['cam_help'] for x in [
 '/base/soc@0/cci@ac4a000/i2c-bus@1/camera@10','/base/soc@0/cci@ac4b000/i2c-bus@1/camera@10']),
              common_r3_payloads_preserved=True,no_test_frames_requested=True)
assert report['standard_cam_enumerated_both']
(R/'postboot-hardware-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(dict(stage=267,new_modules_loaded_and_verified=True,both_pmic_common_drivers=True,
 lab_modules_and_reset_node_absent=True,standard_front_back_enumeration=True,rear_orientation=1,
 rear_crop=d['sensors']['imx319']['selection']['crop'],all_four_rails_off=True,taint=d['taint'])))
