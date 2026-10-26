"""Targeted offline fixtures for the actual read-only postboot audit branches."""
from pathlib import Path
import ast,copy,hashlib,importlib.util,json
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('postboot',HERE/'r7-postboot.py')
p=importlib.util.module_from_spec(spec);spec.loader.exec_module(p)
camera=json.loads((HERE.parents[1]/'kernel440/current-state-validation.json').read_text())
manifest_path=Path('/mnt/e/edk2-samurai-out/charging-management-20261023/r7-candidate/manifest.json')
manifest_text=manifest_path.read_text();meta=json.loads(manifest_text)
assert hashlib.sha256(manifest_path.read_bytes()).hexdigest()==p.MANIFEST_SHA
old='11111111-1111-1111-1111-111111111111';new='22222222-2222-2222-2222-222222222222'
release=meta['release'];version='#363 exact fixture'
def fact(path,digest,mode=0o600):return dict(path=path,resolved=path,sha256=digest,regular=True,symlink=False,uid=0,gid=0,mode=mode)
def module(path,digest):return dict(**fact(path,digest),disk_note_sha256='note',loaded_note_sha256='note',loaded_note_matches_disk=True,intree=dict(exit=0,stdout='Y\n'))
sample=dict(shadow=0,valid=1,online=1,protection_ok=1,budget_ua=100000,temp_decic=240,
 pack_uv=8500000,cell1_uv=4250000,cell2_uv=4250000,flags=0,fault=0,session_seconds=10,
 desired_enable=1,error=0,stop_error=0,latched=0,source_inhibit=0,thermal_inhibit=0,cycle_timeout=0,
 gauge_current_ua=-1000,logical_full=0,full_holding=0,hold_requested=0,full_cause=0,
 sw_full_count=0,recharge_count=0,gauge_charge_stop=0,age_ms=10)
kv=lambda row:' '.join(str(k)+'='+str(v) for k,v in row.items())
raw=dict(boot_id=new,boot_id_after=new,uname=dict(release=release,version=version,machine='aarch64'),
 taint='0',taint_after='0',rootfs=fact('/etc/samurai-rootfs-release','rootfs'),
 manifest=fact('/usr/share/samurai-charging/manifest.json',p.MANIFEST_SHA),manifest_text=manifest_text,
 service=fact('/usr/sbin/samurai-charging',p.SERVICE_SHA),
 installed_files={name:fact(name,digest) for name,digest in meta['installed_files'].items()},
 charging_modules={n:module(meta['modules'][n]['target'],sha) for n,sha in p.CHARGING_SHA.items()},
 retained='Y',charger_driver='samurai-mp2650',boot_enabled=True,
 telemetry_before=kv(sample),telemetry_after=kv(sample),
 source=dict(online='1',usb_type='Unknown [SDP] DCP CDP C',current_max='100000',input_current_limit='100000'),
 charger=dict(online='1',status='Charging',health='Good',charge_behaviour='[auto] inhibit-charge',
  input_current_limit='100000',constant_charge_current='250000',constant_charge_voltage='8725000'),
 protection_state='id=0x2719 safety=0x0 pf=0x0 operation=0x300 manufacturing=0x18 pf_enabled=0 error=0',
 udc=dict(state='configured',current_speed='high-speed'),config_max_power_ma='100',
 package_db='\n\n'.join('P:'+n+'\nV:'+v for n,v in camera['packages'].items()),
 camera_modules={n:module('/camera/'+n,info['sha256']) for n,info in camera['modules'].items()},
 profiles={n:fact(p.PROFILES[n],digest,0o644) for n,digest in camera['private_profiles'].items()},
 camera_runtime={name:fact(name,digest,0o644) for name,digest in p.CAMERA_RUNTIME.items()},
 m2m=json.dumps(dict(users=0,running=False,fatal=False,pinned=False,orphans=0,failed=0,cancelled=0,
  first_error=0,jobs=0,completed=0,direct_completed=0)),
 core=json.dumps({key:0 for key in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups',
  'remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes',
  'watchdogs','protocol_errors','cleanup_error','pc_error']}),
 pm={n:'suspended' for n in p.PM},services={n:[dict(pid=2000+i,uid=10000)] for i,n in enumerate(p.USER_SERVICES)},
 rc_status=dict(exit=0,stdout='\n'.join(' '+n+' [ started 00:00:34 (0) ]' for n in p.RC_SERVICES)),
 remoteprocs={str(i):dict(name=n,state='running') for i,n in enumerate(['modem','adsp','slpi'])},
 hci0_present=True,dmesg=dict(exit=0,stdout='fresh fixture boot; no failures\n'))
expected=dict(camera=camera,old_boot_uuid=old,kernel_release=release,kernel_version=version,
 rootfs_sha256='rootfs',original_key_transport_verified=True,native_ua=100000)

def edit_sample(r,**values):
 for key in ['telemetry_before','telemetry_after']:
  s=p.parse_kv(r[key]);s.update(values);r[key]=kv(s)

cases=[]
def case(label,edit=None,want=True,section=None,expect_edit=None):
 r=copy.deepcopy(raw);e=copy.deepcopy(expected)
 if edit:edit(r)
 if expect_edit:expect_edit(e)
 result=p.audit(r,e)
 assert result['passed']==want,(label,result)
 if section:assert section in result['errors'],(label,result)
 cases.append(label)

case('new boot enabled; fresh PIDs and zero boot counters accepted')
case('hardware Full charge-only hold accepted',lambda r:(edit_sample(r,logical_full=1,desired_enable=0,full_holding=1,hold_requested=1,full_cause=3),r['charger'].update(status='Full')))
case('software Full with hardware Not charging accepted',lambda r:(edit_sample(r,logical_full=1,desired_enable=0,full_holding=1,hold_requested=1,full_cause=1),r['charger'].update(status='Not charging')))
case('Full cannot mask enable contradiction',lambda r:edit_sample(r,logical_full=1,full_holding=1,hold_requested=1,full_cause=1),False,'charging_sample')
case('TCA alone not normal Full',lambda r:edit_sample(r,flags=0x4000,gauge_charge_stop=1,error=-11,desired_enable=0),False,'charging_sample')
case('hard latch wins Full',lambda r:edit_sample(r,logical_full=1,desired_enable=0,full_holding=1,hold_requested=1,full_cause=3,latched=1),False,'charging_sample')
case('stale sample rejected',lambda r:edit_sample(r,age_ms=2000),False,'charging_sample')
case('SDP cannot exceed native100',lambda r:r['source'].update(current_max='500000'),False,'charging_sample')
case('CDP1.5A independent native100 accepted',lambda r:(r['source'].update(usb_type='SDP DCP [CDP]',current_max='1500000'),r['charger'].update(input_current_limit='900000'),edit_sample(r,budget_ua=1500000)))
case('unknown/FLOAT with missing source rejected',lambda r:r['source'].update(usb_type='[Unknown] SDP',current_max={'errno':61}),False,'charging_sample')
case('native ENODATA rejected',lambda r:r['source'].update(input_current_limit={'errno':61}),False,'charging_sample')
case('protected pack mismatch rejected',lambda r:r.update(protection_state=r['protection_state'].replace('0x2719','0x2610')),False,'charging_sample')
case('warm zone cannot retain normal CV',lambda r:edit_sample(r,temp_decic=450,cell1_uv=4100000,cell2_uv=4100000,pack_uv=8200000),False,'charging_sample')
case('pack global lower bound retained',lambda r:edit_sample(r,cell1_uv=2000000,cell2_uv=2000000,pack_uv=3800000),False,'charging_sample')
case('unchanged boot rejected',lambda r:r.update(boot_id=old,boot_id_after=old),False,'new_boot_identity')
case('transport proof mandatory',want=False,section='new_boot_identity',expect_edit=lambda e:e.update(original_key_transport_verified=False))
case('old boot field mandatory',want=False,section='new_boot_identity',expect_edit=lambda e:e.update(old_boot_uuid=None))
case('exact kernel version mandatory',want=False,section='new_boot_identity',expect_edit=lambda e:e.update(kernel_version='#363 wrong'))
case('wrong manifest rejected',lambda r:r['manifest'].update(sha256='old'),False,'charging_install')
case('old loaded USB rejected',lambda r:r['charging_modules']['samurai-usb-input'].update(loaded_note_matches_disk=False),False,'charging_install')
case('private profile mismatch rejected',lambda r:r['profiles']['imx471'].update(sha256='old'),False,'camera440')
case('idle camera cannot retain DMA',lambda r:r.update(core=r['core'].replace('"mapped_bytes": 0','"mapped_bytes": 4096')),False,'camera440')
case('duplicate UID10000 service rejected',lambda r:r['services']['phosh'].append(dict(pid=9000,uid=10000)),False,'camera440')
case('SensorProxy must be started',lambda r:r['rc_status'].update(stdout=r['rc_status']['stdout'].replace('iio-sensor-proxy [ started','iio-sensor-proxy [ stopped')),False,'services_faults')
case('boot warning retained and rejected',lambda r:r['dmesg'].update(stdout='WARNING: fixture'),False,'services_faults')

ast.parse((HERE/'r7-postboot.py').read_text())
ko=manifest_path.parent/'samurai-usb-input.ko'
note=p.elf_note(ko.read_bytes());assert note
result=dict(passed=True,branch_vectors=len(cases),cases=cases,actual_r7_elf_note_parsed=True,
 candidate_sha256=hashlib.sha256((HERE/'r7-postboot.py').read_bytes()).hexdigest(),
 collector_executed=False,device_access=False,physical_acceptance=False)
(HERE/'r7-postboot-test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
