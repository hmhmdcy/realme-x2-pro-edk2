"""One-shot read-only R7 postboot evidence. No SSH, control, REG14 or SDK.

Root injects EXPECTED_CAMERA, OLD_BOOT_UUID, EXPECTED_KERNEL_RELEASE,
EXPECTED_KERNEL_VERSION, EXPECTED_ROOTFS_SHA256 and
ORIGINAL_KEY_TRANSPORT_VERIFIED=True through its original pinned-key transport.
This script cannot independently authenticate its own transport. All raw reads
and failures are printed before its nonzero exit. It never adopts a boot guard.
READ_PMIC_STATUS may be injected True for the seven established read-only GETs.
"""
from pathlib import Path
import hashlib,json,os,re,stat,struct,subprocess,sys,time

MANIFEST_SHA='5638db4c183ec502ed1df4facfe91111d1956754bb2338a5ddaf8838e9552c68'
SERVICE_SHA='61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4'
CHARGING_SHA={
 'samurai-mp2650':'fac827cfd3d1d847cb1db82f0a29e451652bd16a996b20666be2d9b330889cb6',
 'samurai-usb-input':'7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70',
 'samurai-gauge-protection':'75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7'}
PROFILES={n:'/etc/libcamera/ipa/camss-vfe/'+n+'.yaml' for n in ['s5kgw1','imx319','s5k3m5','imx471']}
# Exact actual install-proof-r3-private.json paths/hashes, not package names only.
CAMERA_RUNTIME={
 '/usr/lib/libcamera.so.0.7.2':'0884c73489815132b5f180c303ab5ed2edc4c52f0f7b191365054aa855849a48',
 '/usr/lib/libcamera-base.so.0.7.2':'6e505f4996f68bbf38c680ee517bd570b90e4bbe73906b4da7673b573e89f50d',
 '/usr/lib/libcamera/ipa/ipa_camss_vfe.so':'8703093d5882488e7a0125002a71e5a23f5382594b0a5b4ae30f9ed0d63ec796',
 '/usr/lib/libcamera/ipa/ipa_camss_vfe.so.sign':'c9546260b98ffbefbc04aa0e7efa47e225c381c9236badf7e554ab9034dafd97',
 '/usr/libexec/libcamera/camss_ipa_proxy':'79fad5aad1cb8c7fe45d8608f1efbac6f246377741dfcb0dc88ae3ce8c8a728e',
 '/usr/lib/gstreamer-1.0/libgstlibcamera.so':'ada72c44fe240e4f0d27324d708b3bebf97650756c28e323b35c4e8b19d4ac70',
 '/usr/libexec/libcamera/v4l2-compat.so':'4a4203f6ed70ebfb19a2182b6eca3cb015ddd909f11053ca879c74101996299b',
 '/usr/bin/cam':'1f6251d8202c4740716f5116a603f33be5e5b577e0e8f48f23a74776e1ff0a05'}
PM=['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']
USER_SERVICES=['phoc','phosh','pipewire','wireplumber']
RC_SERVICES=['samurai-charging','bluetooth','samurai-ssc','iio-sensor-proxy','greetd']
FAULTS=['WARNING:','Oops:','refcount_t: underflow','cannot create duplicate filename',
 'gpu fault:','NGD resume failed','fatal error received','Unhandled context fault:',
 'Kernel panic - not syncing','Unable to handle kernel']
BANDS=[(-20,0,250000,3980000,3990000),(0,50,900000,4400000,4410000),
 (50,120,1100000,4400000,4410000),(120,160,1100000,4400000,4410000),
 (160,440,1100000,4400000,4410000),(440,530,550000,4130000,4140000)]
sha=lambda raw:hashlib.sha256(raw).hexdigest()

def attempt(fn):
 try:return fn()
 except Exception as e:return {'error':type(e).__name__,'message':str(e),'errno':getattr(e,'errno',None)}

def read(path):return attempt(lambda:Path(path).read_text().strip())

def command(args):
 def run():
  q=subprocess.run(args,capture_output=True,text=True,timeout=8)
  return {'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr}
 return attempt(run)

def file_fact(path):
 p=Path(path);raw=p.read_bytes();s=p.lstat()
 return {'path':str(p),'resolved':str(p.resolve()),'sha256':sha(raw),
  'mode':stat.S_IMODE(s.st_mode),'uid':s.st_uid,'gid':s.st_gid,
  'regular':stat.S_ISREG(s.st_mode),'symlink':p.is_symlink()}

def elf_note(raw):
 assert raw[:6]==b'\x7fELF\x02\x01' and len(raw)>=64,'not ELF64LE'
 off=struct.unpack_from('<Q',raw,40)[0]
 stride,count,strings=struct.unpack_from('<HHH',raw,58)
 assert stride>=64 and 0<count<65536 and strings<count and off+stride*count<=len(raw)
 rows=[struct.unpack_from('<IIQQQQIIQQ',raw,off+i*stride) for i in range(count)]
 def data(row):
  assert row[4]+row[5]<=len(raw)
  return raw[row[4]:row[4]+row[5]]
 names=data(rows[strings]);notes=[]
 for row in rows:
  assert row[0]<len(names)
  if names[row[0]:].split(b'\0',1)[0]==b'.note.gnu.build-id':notes.append(data(row))
 assert len(notes)==1 and notes[0]
 return notes[0]

def module_fact(name,path):
 p=Path(path);r=file_fact(p);disk=elf_note(p.read_bytes())
 loaded=Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()
 r.update(disk_note_sha256=sha(disk),loaded_note_sha256=sha(loaded),
  loaded_note_matches_disk=loaded==disk,intree=command(['modinfo','-F','intree',str(p)]))
 return r

def parse_kv(text):
 assert isinstance(text,str),'unreadable key=value text'
 result={}
 for item in text.split():
  key,value=item.split('=',1);assert key not in result
  result[key]=int(value,16) if value.lower().startswith('0x') else int(value)
 return result

def active(text):
 assert isinstance(text,str),'unreadable active choice'
 found=re.findall(r'\[([^]]+)\]',text)
 return found[0] if len(found)==1 else text.strip() if not found and len(text.split())==1 else None

def pmic_status():
 # The same bounded GET protocol used by query-fixed-telemetry.py77–96.
 p=Path('/sys/kernel/debug/regmap/0-02')
 assert (p/'name').read_text().strip()=='pmic-spmi'
 assert (p/'range').read_text()=='0-ffff\n'
 fd=os.open(p/'registers',os.O_RDONLY|os.O_CLOEXEC)
 try:
  result={}
  for reg in [0x1307,0x1308,0x1310,0x1506,0x1509,0x150b,0x150d]:
   line=os.pread(fd,9,reg*9);match=re.fullmatch(rb'([0-9a-f]{4}): ([0-9a-f]{2})\n',line)
   assert match and int(match[1],16)==reg
   result[hex(reg)]=int(match[2],16)
  return result
 finally:os.close(fd)

def collect(expected_camera,read_pmic=False):
 raw={'boot_id':read('/proc/sys/kernel/random/boot_id'),'uname':dict(zip(
  ['sysname','nodename','release','version','machine'],os.uname())),
  'taint':read('/proc/sys/kernel/tainted'),
  'rootfs':attempt(lambda:file_fact('/etc/samurai-rootfs-release')),
  'boottime':time.clock_gettime(time.CLOCK_BOOTTIME)}
 raw['manifest_text']=read('/usr/share/samurai-charging/manifest.json')
 raw['manifest']=attempt(lambda:file_fact('/usr/share/samurai-charging/manifest.json'))
 raw['service']=attempt(lambda:file_fact('/usr/sbin/samurai-charging'))
 meta=attempt(lambda:json.loads(raw['manifest_text']))
 raw['installed_files']={p:attempt(lambda p=p:file_fact(p)) for p in meta.get('installed_files',{})}
 release=os.uname().release
 raw['charging_modules']={n:attempt(lambda n=n:module_fact(n.replace('-','_'),
  '/lib/modules/'+release+'/extra/samurai-charging/'+n+'.ko')) for n in CHARGING_SHA}
 raw['retained']=read('/sys/module/samurai_usb_input/parameters/native_retained')
 raw['charger_driver']=attempt(lambda:Path('/sys/bus/i2c/devices/0-005c/driver').resolve().name)
 raw['boot_enabled']=Path('/etc/runlevels/default/samurai-charging').is_symlink()
 client=Path('/sys/bus/i2c/devices/0-005c');ps=Path('/sys/class/power_supply')
 raw['telemetry_before']=read(client/'telemetry')
 raw['source']={n:read(ps/'samurai-usb-input'/n) for n in ['online','usb_type','current_max','input_current_limit']}
 raw['charger']={n:read(ps/'mp2650-input'/n) for n in ['status','health','online','charge_behaviour',
  'input_current_limit','constant_charge_current','constant_charge_voltage']}
 raw['protection_state']=read('/sys/devices/platform/samurai-gauge-protection/protection_state')
 raw['telemetry_after']=read(client/'telemetry')
 raw['udc']={n:read(Path('/sys/class/udc/a600000.usb')/n) for n in ['state','current_speed']}
 raw['config_max_power_ma']=read('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower')
 raw['pmic_status']=attempt(pmic_status) if read_pmic else {'not_requested':True}
 raw['package_db']=read('/lib/apk/db/installed')
 raw['camera_modules']={}
 for name in expected_camera.get('modules',{}):
  def get_module(name=name):
   assert name in ['qcom_camss','qcom_camss_icp_a5_core','camss_icp_a5_m2m']
   q=command(['modinfo','-n',name]);assert q['exit']==0
   return module_fact(name,q['stdout'].strip())
  raw['camera_modules'][name]=attempt(get_module)
 raw['profiles']={n:attempt(lambda p=p:file_fact(p)) for n,p in PROFILES.items()}
 raw['camera_runtime']={p:attempt(lambda p=p:file_fact(p)) for p in CAMERA_RUNTIME}
 cam=Path('/sys/bus/platform/devices/ac10000.icp')
 raw['m2m']=read(cam/'m2m_status');raw['core']=read(cam/'state')
 raw['pm']={n:read(Path('/sys/bus/platform/devices')/n/'power/runtime_status') for n in PM}
 raw['services']={n:[] for n in USER_SERVICES}
 for p in Path('/proc').glob('[0-9]*'):
  try:
   name=(p/'comm').read_text().strip()
   if name in raw['services'] and (p/'stat').read_text().rsplit(')',1)[1].split()[0]!='Z':
    raw['services'][name].append({'pid':int(p.name),'uid':p.stat().st_uid})
  except OSError:pass
 # rc-status reads OpenRC state; do not call samurai-charging status, whose
 # installed main writes its state receipt even for a status action.
 raw['rc_status']=command(['rc-status','--all'])
 raw['remoteprocs']={p.name:{'name':read(p/'name'),'state':read(p/'state')} for p in Path('/sys/class/remoteproc').glob('*')}
 raw['hci0_present']=Path('/sys/class/bluetooth/hci0').exists()
 raw['sensor_power']=read('/sys/devices/platform/sensor-power/state')
 raw['dmesg']=command(['dmesg'])
 raw['boot_id_after']=read('/proc/sys/kernel/random/boot_id')
 raw['taint_after']=read('/proc/sys/kernel/tainted')
 return raw

def check_file(f,digest):
 assert f['sha256']==digest and f['regular'] and not f['symlink']
 assert f['uid']==0 and not f['mode']&0o022

def check_identity(r,e):
 assert e['original_key_transport_verified'] is True,'transport attestation absent'
 assert isinstance(e['old_boot_uuid'],str) and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',e['old_boot_uuid'])
 assert r['boot_id']==r['boot_id_after'] and r['boot_id']!=e['old_boot_uuid']
 assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',r['boot_id'])
 assert r['uname']['release']==e['kernel_release']
 assert r['uname']['version']==e['kernel_version'] and r['uname']['version'].startswith('#363 ')
 assert r['uname']['machine']=='aarch64' and r['taint']==r['taint_after']=='0'
 check_file(r['rootfs'],e['rootfs_sha256'])
 return {'new_boot':True,'transport_proof':'external original-key attestation'}

def check_charging_install(r):
 check_file(r['manifest'],MANIFEST_SHA);check_file(r['service'],SERVICE_SHA)
 meta=json.loads(r['manifest_text'])
 assert meta['adapter_revision']=='r7' and meta['release']==r['uname']['release']
 assert set(meta['modules'])==set(CHARGING_SHA)
 assert set(r['installed_files'])==set(meta['installed_files'])
 for p,digest in meta['installed_files'].items():check_file(r['installed_files'][p],digest)
 for n,digest in CHARGING_SHA.items():
  info=r['charging_modules'][n];check_file(info,digest)
  assert info['loaded_note_matches_disk'] and info['disk_note_sha256']==info['loaded_note_sha256']
  assert info['intree']['exit']==0 and info['intree']['stdout'].strip()=='Y'
  assert meta['modules'][n]['sha256']==digest and meta['modules'][n]['target']==info['path']
 assert r['retained']=='Y' and r['charger_driver']=='samurai-mp2650' and r['boot_enabled']
 return {'disk_and_loaded_r7':True,'service_sha256':SERVICE_SHA}

def check_charging_sample(r,expected_native=100000):
 source=r['source'];charger=r['charger'];kind=active(source['usb_type'])
 assert source['online']==charger['online']=='1'
 native=int(source['input_current_limit']);budget=int(source['current_max'])
 assert native==expected_native and 0<=native<=500000
 assert (kind=='SDP' and budget==native and 50000<=budget<=500000) or (kind=='CDP' and budget==1500000)
 assert r['udc']['state']=='configured' and int(r['config_max_power_ma'])==100
 assert charger['health']=='Good' and active(charger['charge_behaviour'])=='auto'
 ilim=int(charger['input_current_limit']);cc=int(charger['constant_charge_current']);cv=int(charger['constant_charge_voltage'])
 assert 50000<=ilim<=min(900000,budget) and ilim%50000==0
 assert 200000<=cc<=250000 and cc%50000==0
 assert 7425000<=cv<=8725000 and cv%2==0 and (cv//2-3712500)%12500==0
 classifications=[]
 for key in ['telemetry_before','telemetry_after']:
  s=parse_kv(r[key]);assert all(s[k]==1 for k in ['valid','online','protection_ok'])
  assert not any(s[k] for k in ['shadow','fault','error','stop_error','latched','source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop'])
  assert 0<=s['age_ms']<2000 and 0<=s['session_seconds']<36000
  assert s['budget_ua']==budget and not s['flags']&0xc000
  assert 2000000<=s['cell1_uv']<=4600000 and 2000000<=s['cell2_uv']<=4600000
  assert 4000000<=s['pack_uv']<=9200000
  assert abs(s['cell1_uv']+s['cell2_uv']-s['pack_uv'])<=200000
  band=next(b for b in BANDS if b[0]<=s['temp_decic']<b[1])
  assert max(s['cell1_uv'],s['cell2_uv'])<=band[4]
  assert cc<=band[2] and cv//2<=min(4362500,band[3])
  if s['logical_full']:
   assert s['desired_enable']==0 and s['full_holding']==s['hold_requested']==1
   assert s['full_cause'] in [1,2,3]
   classifications.append('healthy_full_charge_only_hold')
  else:
   assert s['desired_enable']==1 and s['full_holding']==s['hold_requested']==0
   classifications.append('healthy_charge_enabled')
 assert charger['status'] in ['Charging','Full','Not charging']
 # Hardware STATUS can differ from logical software Full; never write or force it.
 p=parse_kv(r['protection_state'])
 assert p['id']==0x2719 and p['error']==p['safety']==p['pf']==0
 assert p['operation']&0x300==0x300 and not p['operation']&((1<<20)|(1<<16)|0x7c00)
 assert p['manufacturing']&0x18==0x18 and not p['manufacturing']&0x8006
 assert p['pf_enabled']==int(bool(p['manufacturing']&0x40))
 return {'states':classifications,'source_type':kind,'source_budget_ua':budget,'native_ua':native,
  'input_limit_ua':ilim,'charge_current_ua':cc,'pack_target_uv':cv,'pf_enabled_inherited':p['pf_enabled']}

def check_camera(r,expected):
 versions={}
 for block in r['package_db'].split('\n\n'):
  fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if fields.get('P') in expected['packages']:versions[fields['P']]=fields['V']
 assert versions==expected['packages']
 assert set(expected['modules'])=={'qcom_camss','qcom_camss_icp_a5_core','camss_icp_a5_m2m'}
 for n,entry in expected['modules'].items():
  info=r['camera_modules'][n];check_file(info,entry['sha256'])
  assert info['loaded_note_matches_disk'] and info['disk_note_sha256']==info['loaded_note_sha256']
  assert info['intree']['exit']==0 and info['intree']['stdout'].strip()=='Y'
 assert set(expected['private_profiles'])==set(PROFILES)
 for n,digest in expected['private_profiles'].items():
  info=r['profiles'][n];check_file(info,digest)
  assert info['path']==PROFILES[n] and info['mode']==0o644 and info['gid']==0
 for p,digest in CAMERA_RUNTIME.items():check_file(r['camera_runtime'][p],digest)
 m=json.loads(r['m2m']);c=json.loads(r['core'])
 assert not any(m[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
 assert m['jobs']==m['completed']==m['direct_completed']
 assert not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups',
  'remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes',
  'watchdogs','protocol_errors','cleanup_error','pc_error'])
 assert all(r['pm'][n]=='suspended' for n in PM)
 assert all(len(r['services'][n])==1 and r['services'][n][0]['uid']==10000 for n in USER_SERVICES)
 return {'formal440_files_and_434_notes':True,'idle':True,'new_boot_processes':r['services']}

def check_services_faults(r):
 rc=r['rc_status'];assert rc['exit']==0
 text=re.sub(r'\x1b\[[0-9;]*m','',rc['stdout'])
 for n in RC_SERVICES:assert re.search(r'^\s*'+re.escape(n)+r'\s+\[\s*started(?:\s+[^]\r\n]*)?\]',text,re.M),n
 assert r['hci0_present']
 remote={row['name']:row['state'] for row in r['remoteprocs'].values()}
 assert all(remote[n]=='running' for n in ['modem','adsp','slpi'])
 assert r['dmesg']['exit']==0
 counts={token:r['dmesg']['stdout'].count(token) for token in FAULTS}
 assert not any(counts.values()),counts
 return {'services_started':RC_SERVICES,'remoteprocs':remote,'boot_fault_counts':counts}

def audit(raw,expected):
 result={'passed':False,'checks':{},'errors':{},'read_only':True,'physical_icon_or_sdp500_accepted':False}
 for name,fn in [('new_boot_identity',lambda:check_identity(raw,expected)),
  ('charging_install',lambda:check_charging_install(raw)),
  ('charging_sample',lambda:check_charging_sample(raw,expected.get('native_ua',100000))),
  ('camera440',lambda:check_camera(raw,expected['camera'])),
  ('services_faults',lambda:check_services_faults(raw))]:
  try:result['checks'][name]=fn()
  except Exception as e:result['errors'][name]={'type':type(e).__name__,'message':str(e)}
 result['passed']=len(result['checks'])==5 and not result['errors']
 return result

def main():
 expected={'camera':globals().get('EXPECTED_CAMERA',{}),'old_boot_uuid':globals().get('OLD_BOOT_UUID'),
  'kernel_release':globals().get('EXPECTED_KERNEL_RELEASE'),'kernel_version':globals().get('EXPECTED_KERNEL_VERSION'),
  'rootfs_sha256':globals().get('EXPECTED_ROOTFS_SHA256'),
  'original_key_transport_verified':globals().get('ORIGINAL_KEY_TRANSPORT_VERIFIED',False),
  'native_ua':globals().get('EXPECTED_NATIVE_UA',100000)}
 report={'scope':'one-shot read-only R7 new-boot validation; no guard adoption or physical acceptance'}
 try:
  report['raw']=collect(expected['camera'],globals().get('READ_PMIC_STATUS',False))
  report['result']=audit(report['raw'],expected)
 except Exception as e:report['result']={'passed':False,'collection_error':type(e).__name__,'message':str(e)}
 print(json.dumps(report),flush=True)
 return 0 if report['result']['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
