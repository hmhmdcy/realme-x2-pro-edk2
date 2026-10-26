"""Rollback-aware read-only gates; same hardware tail and original service lock."""
import base64,fcntl,hashlib,json,os,re,runpy,stat,struct,sys,time,uuid
from pathlib import Path
ROOT=Path("/root/charging-management-20261023")
SERVICE_LOCK="/run/lock/samurai-charging.lock"
_SERVICE_FD=None
LIVE_PATH='/usr/lib/samurai-charging/live-session.py'
LIVE_SHA='2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
BOOT='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
LOGDUMP='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
OLD='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
OLD_NOTES={'samurai-usb-input': 'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0', 'samurai-gauge-protection': '930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76', 'samurai-mp2650': 'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
OLD_FILES={'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': '75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7', '/usr/share/samurai-charging/manifest.json': '320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'}
CAMERA481='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
SENSOR468_NOTE='a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13'
EXPECTED_MANIFEST={'release': '7.3.0-rc6-rmx1931-samurai-k363+', 'modules': {'samurai-mp2650': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', 'sha256': '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f'}, 'samurai-usb-input': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', 'sha256': '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70'}, 'samurai-gauge-protection': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko', 'sha256': '75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7'}}, 'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000, 'source_budget_enforced': True, 'installed_files': {'/usr/sbin/samurai-charging': '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4', '/etc/init.d/samurai-charging': 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', '/usr/lib/samurai-charging/control-trial.py': 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761', '/usr/lib/samurai-charging/live-session.py': '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': '10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': '7d4e0f948b993a6e0cc9459bac4ade2db2fe7b88ce7b7d462ea34bcb933c4f70', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': '75b97e0d6b906ec600171ce68adec6f25a91556758f76bbf3d563cf831e783c7'}, 'adapter_revision': 'r8'}
STARTUP_PATH="/usr/local/sbin/samurai-usb"
STARTUP_SHA="2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a"
PROOF_SHA='686b9ab164eeda5aefd558b2c8f283e31269ca75eb14b4bc007c1e0acf8a2552'

def secure_file(path):
 p=Path(path);assert p.is_file() and not p.is_symlink(),str(p)
 s=p.stat();assert s.st_uid==0 and not s.st_mode&0o022,str(p)
 return p


def file_sha(path):
 return hashlib.sha256(secure_file(path).read_bytes()).hexdigest()


def block_sha(path,expected_bytes):
 # This is the existing read-only by-partlabel boundary, with an actual block
 # size check. Never read a writable mapping or use blockdev's mutation paths.
 fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC)
 try:
  assert stat.S_ISBLK(os.fstat(fd).st_mode)
  assert struct.unpack('=Q',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]==expected_bytes
  digest=hashlib.sha256();remaining=expected_bytes
  while remaining:
   data=os.read(fd,min(1048576,remaining));assert data,'short partition read'
   digest.update(data);remaining-=len(data)
  return digest.hexdigest()
 finally:os.close(fd)


def camera481_check(wrapper):
 assert file_sha(wrapper)==CAMERA481
 expected=json.loads(Path(wrapper).read_bytes());assert expected['validated']
 expected=expected['expected'];assert expected['kernel_release']==os.uname().release
 for name,digest in expected['installed_files'].items():assert file_sha(name)==digest,name
 for name,info in expected['modules'].items():
  assert file_sha(info['path'])==info['sha256']
  assert hashlib.sha256(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes()).hexdigest()==info['note']
  assert Path('/sys/module',name,'initstate').read_text().strip()=='live'
 assert hashlib.sha256(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()).hexdigest()==SENSOR468_NOTE
 assert Path('/sys/module/s5k3m5/initstate').read_text().strip()=='live'
 versions={}
 for block in Path('/lib/apk/db/installed').read_text().split('\n\n'):
  fields=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if fields.get('P') in expected['packages']:versions[fields['P']]=fields.get('V')
 assert versions==expected['packages']


def eud_off_check():
 # Firmware keeps COM disabled. No MMIO or driver control is part of this gate.
 node=Path('/sys/firmware/devicetree/base/soc@0/serial@88e0000')
 assert (node/'compatible').read_bytes()==b'qcom,sm8150-eud-com\0'
 assert (node/'status').read_bytes()==b'disabled\0'
 assert not Path('/sys/bus/platform/devices/88e0000.serial/driver').exists()
 driver=Path('/sys/bus/platform/drivers/qcom_eud_com')
 assert not list(driver.glob('*.serial'))
 assert not list(Path('/sys/class/tty').glob('ttyEUD*'))
 assert not any('eud' in line.lower() for line in Path('/proc/consoles').read_text().splitlines())
 assert not any(t.startswith(('earlycon=eud','console=eud')) for t in Path('/proc/cmdline').read_text().split())


def charging_sample_phase(sample, stopped=False):
 full=(sample['logical_full']==sample['hold_requested']==sample['full_holding']==1 and sample['full_cause'] in (1,2,3) and sample['desired_enable']==0 and sample['session_seconds']==0)
 if stopped:
  return sample['desired_enable']==sample['hold_requested']==sample['full_holding']==0 and (sample['logical_full']==0 and sample['full_cause']==0 or sample['logical_full']==1 and sample['full_cause'] in (1,2,3) and sample['session_seconds']==0)
 return full if any(sample[k] for k in ['logical_full','hold_requested','full_holding','full_cause']) else sample['desired_enable']==1


def safe_sample(data, now):
    s = data['sample']
    need(s.get('valid') == s.get('protection_ok') == s.get('online') == 1 and
         s.get('shadow') == 0 and 0 <= s.get('age_ms', -1) <= 3000, 'fresh complete online protection sample')
    need(all(s.get(k, -1) == 0 for k in ['error', 'stop_error', 'latched', 'fault', 'source_inhibit',
                                       'cycle_timeout', 'thermal_inhibit', 'gauge_charge_stop']), 'no fault/timeout/gauge or thermal stop')
    need('flags' in s and not s['flags'] & 0xc000 and 0 <= s.get('session_seconds', -1) < 36000, 'safe raw flags/session')
    need(all(2000000 <= s.get(key, 0) <= 4600000 for key in ['cell1_uv', 'cell2_uv']) and
         4000000 <= s.get('pack_uv', 0) <= 9200000 and
         abs(s['cell1_uv'] + s['cell2_uv'] - s['pack_uv']) <= 200000, 'safe complete pack/cell values')
    need(160 <= s.get('temp_decic', -999) < 440 and s.get('thermal_band') == 4, 'known safe NORMAL window')
    need(0 <= data['read_end'] - data['read_start'] <= 3 and 0 <= now - data['read_end'] <= 1, 'fresh bounded observation')
    p = data['protection']
    need(data['protection_health'] == 'Good' and p.get('id') == 0x2719 and p.get('error') == p.get('safety') == p.get('pf') == 0,
         'independent fresh protection state')
    need(p.get('operation', 0) & 0x300 == 0x300 and not p['operation'] & ((1 << 20) | (1 << 16) | 0x7c00) and
         p.get('manufacturing', 0) & 0x18 == 0x18 and not p['manufacturing'] & 0x8006, 'sealed autonomous factory protection')
    need(data['notes'] == OLD_NOTES and data['openrc_started'] is True, 'old resident modules and service retained')


def environment(data):
    state = data['state']
    need(state['taint'] == '0' and state['driver'] == 'samurai-mp2650' and
         len(state['camera_pm']) == 4 and all(v == 'suspended' for v in state['camera_pm'].values()), 'idle camera and managed charger')
    m2m = json.loads(state['m2m'])
    need(all(m2m.get(k) == 0 for k in ['users', 'orphans', 'jobs', 'first_error']) and
         all(m2m.get(k) is False for k in ['running', 'fatal', 'pinned']), 'idle camera m2m')
    services = state['services']
    need(len(services) == 4 and {s['comm'] for s in services} == {'phoc', 'phosh', 'pipewire', 'wireplumber'} and
         all(s['uid'] == 10000 and s['pid'] > 0 for s in services), 'actual four session processes')


def active(text):
 assert isinstance(text,str),'unreadable active choice'
 found=re.findall(r'\[([^]]+)\]',text)
 return found[0] if len(found)==1 else text.strip() if not found and len(text.split())==1 else None


def need(value,message):
 if not value:raise ValueError(message)


def sha(raw):return hashlib.sha256(raw).hexdigest()


def owned_directory(path):
 p=Path(path);s=p.lstat()
 need(stat.S_ISDIR(s.st_mode) and not p.is_symlink() and s.st_uid==0 and stat.S_IMODE(s.st_mode)==0o700,'owned directory: '+str(p))
 return p


def raw_owned(path,limit=4_000_000):
 p=secure_file(path);s=p.stat()
 need(s.st_size<=limit and stat.S_IMODE(s.st_mode)==0o600,'bounded private raw: '+str(p))
 return p.read_bytes()


def process_observation(receipt):
 pid=receipt['pid'];need(type(pid) is int and pid>0,'retained positive PID')
 try:fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
 except FileNotFoundError:return {'state':'absent','pid':pid}
 except (OSError,ValueError,IndexError):return {'state':'unknown','pid':pid}
 try:ticks=int(fields[19])
 except (ValueError,IndexError):return {'state':'unknown','pid':pid}
 if ticks!=receipt['start_ticks']:return {'state':'pid_reused','pid':pid}
 return {'state':'zombie' if fields[0]=='Z' else 'alive','pid':pid,'start_ticks':ticks}


def observe_staged():
 need(file_sha(LIVE_PATH)==LIVE_SHA,'fixed read-only live library')
 live=runpy.run_path(LIVE_PATH)
 need(file_sha(LIVE_PATH)==LIVE_SHA and live['REGS']==[0,1,2,3,4,5,7,8,9,15,19],'stable non-destructive register set')
 start=time.clock_gettime(time.CLOCK_BOOTTIME);state=live['state']()
 ps=Path('/sys/class/power_supply');supply=ps/'mp2650-input'
 protection=Path('/sys/devices/platform/samurai-gauge-protection/protection_state').read_text()
 result={'read_start':start,'state':state,
  'sample':{k:int(v) for k,v in (p.split('=') for p in Path('/sys/bus/i2c/devices/0-005c/telemetry').read_text().split())},
  'source':{k:(ps/'samurai-usb-input'/k).read_text().strip() for k in ['online','usb_type','current_max','input_current_limit']},
  'notes':{name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES},
  'openrc_started':Path('/run/openrc/started/samurai-charging').exists(),
  'protection':{k:int(v,0) for k,v in (p.split('=') for p in protection.split())},
  'protection_health':(ps/'samurai-gauge-protection/health').read_text().strip(),
  'charge_behaviour':(supply/'charge_behaviour').read_text().strip(),
  'limits':{'input_ua':int((supply/'input_current_limit').read_text()),'charge_ua':int((supply/'constant_charge_current').read_text()),
    'cv_pack_uv':int((supply/'constant_charge_voltage').read_text())}}
 result['read_end']=time.clock_gettime(time.CLOCK_BOOTTIME)
 return result


def staged_health(data,now):
 safe_sample(data,now)
 s,r,lim=data['sample'],data['state']['registers'],data['limits']
 need(charging_sample_phase(s,True) and active(data['charge_behaviour'])=='inhibit-charge' and r['08']&0x18==8,'stage INHIBIT still held')
 source=data['source'];kind=active(source['usb_type'])
 need(source['online']=='1','actual online source')
 budget,native=int(source['current_max']),int(source['input_current_limit'])
 need(native==500000 and ((kind=='SDP' and budget==500000) or
  (kind in ['CDP','DCP'] and budget==1500000) or (kind=='C' and budget in [1500000,3000000])),'fresh known source/native500 budget')
 need(s['budget_ua']==budget and lim['input_ua']==min(900000,budget) and lim['charge_ua']==250000,'fresh source authority/caps')
 need((r['00']&0x7f)*50000==(r['0f']&0x7f)*50000==lim['input_ua'] and
  (r['02']&0x7f)*50000==lim['charge_ua'],'both actual input and charge limits')
 need(7425000<=lim['cv_pack_uv']<=8725000 and lim['cv_pack_uv']==2*(3712500+((r['04']&0x7e)>>1)*12500),'inherited CV')
 state=data['state'];need(state['taint']=='0' and state['driver']=='samurai-mp2650','current untainted provider')
 need(len(state['camera_pm'])==4 and all(v=='suspended' for v in state['camera_pm'].values()),'idle actual camera')
 m=json.loads(state['m2m'])
 need(all(m.get(k)==0 for k in ['users','orphans','jobs','first_error']) and
  all(m.get(k) is False for k in ['running','fatal','pinned']),'no active camera work')
 return {'stage_INHIBIT_reverified':True,'source':kind,'budget_ua':budget,'hardware_input_ua':lim['input_ua']}


def acquire_service_lock():
 global _SERVICE_FD
 need(_SERVICE_FD is None,'single lock acquisition')
 fd=os.open(SERVICE_LOCK,os.O_RDWR|os.O_NOFOLLOW)
 try:
  info=os.fstat(fd);need(stat.S_ISREG(info.st_mode) and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o600,'original service lock')
  fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
 except BaseException:os.close(fd);raise
 _SERVICE_FD=fd


def rollback_material(meta):
 proof_path=secure_file(ROOT/meta['transaction_id']/'proof.py')
 need(file_sha(proof_path)==PROOF_SHA,'pinned rollback qualifier')
 proof=runpy.run_path(str(proof_path)); rollback=meta['rollback']
 need(set(rollback)=={'transaction_id','request_sha256','result_sha256','host_binding_sha256','worker_sha256','supervisor_sha256','evidence'},'rollback evidence fields')
 paths=proof['remote_paths'](rollback['transaction_id'])
 need(set(paths)==set(rollback['evidence']),'exact rollback evidence set')
 raw={}
 for key,path in paths.items():
  item=rollback['evidence'][key]
  need(item=={'path':path,'sha256':item['sha256']} and re.fullmatch('[0-9a-f]{64}',item['sha256']),'canonical rollback path/hash')
  raw[key]=raw_owned(path,limit=8_000_000)
  need(sha(raw[key])==item['sha256'],'rollback original changed: '+key)
 need(sha(raw['request'])==rollback['request_sha256'] and sha(raw['result'])==rollback['result_sha256'],'rollback request/result')
 need(sha(raw['worker_source'])==rollback['worker_sha256']==proof['WORKER'] and
  sha(raw['supervisor_source'])==rollback['supervisor_sha256']==proof['SUPERVISOR'],'original rollback sources')
 root=owned_directory(ROOT/rollback['transaction_id']);owned_directory(root/'device-rollback')
 worker=runpy.run_path(str(root/'restore-worker.py'))
 from types import SimpleNamespace
 module=SimpleNamespace(**worker);request=json.loads(raw['request']);result=json.loads(raw['result'])
 names={'result':'result.json','worker_process':'process-private.json','worker_launch':'worker-launch-receipt-private.json',
  'worker_terminal':'worker-terminal-private.json','supervisor_launch':'launch-receipt-private.json',
  'supervisor_process':'supervisor-process-private.json','supervisor_terminal':'supervisor-terminal-private.json',
  'before':'before-private.json','stopped':'stopped-private.json','after':'after-private.json'}
 process={}
 for key,role in [('worker_process','process'),('supervisor_process','supervisor_process')]:
  observed=process_observation(json.loads(raw[key]));process[role]=observed
 response={'transaction_id':request['transaction_id'],'request_sha256':sha(raw['request']),
  'worker_terminal_verified':True,'worker_terminal':json.loads(raw['worker_terminal']),'worker_result':result,
  'files':{name:{'base64':base64.b64encode(raw[key]).decode(),'bytes':len(raw[key]),'sha256':sha(raw[key])} for key,name in names.items()},**process}
 proof['validate_records'](request,raw['request'],response,module)
 need(request['identity']=={'boot_id':meta['boot_id'],'version':meta['kernel_version'],
  'serial_sha256':meta['soc_serial_sha256'],'compatible_sha256':meta['compatible_sha256'],
  'rootfs_sha256':meta['rootfs_release_sha256']} and request['profile']==meta['profile'],'current rollback identity')
 # The frozen source verifier is read-only except for one evidence-log call.
 # Reuse its actual verifier with only that log sink suppressed; no Device.begin,
 # stop, replace, close or publish method is called here.
 reader=SimpleNamespace(log=lambda name,value:None)
 module.Device.source_proof(reader,request)
 expected_boot,expected_notes=module.expected_profile(request)
 need(meta['current_boot_sha256']==expected_boot and meta['resident_notes']==expected_notes,'explicit rollback profile constants')
 return request,module


def validate_meta_shape(meta,guard_path):
 need(guard_path.is_absolute() and guard_path.name=='guard-private.json','private guard path')
 need(set(meta)=={'schema','transaction_id','token','boot_id','kernel_release','kernel_version','soc_serial_sha256',
  'compatible_sha256','rootfs_release_sha256','profile','current_boot_sha256','rollback_boot_sha256',
  'unchanged_logdump_sha256','boot_bytes','logdump_bytes','resident_notes','rollback','post_restore_probe',
  'partitions','disk_state','runtime_validation_accepted'},'exact rollback restart fields')
 need(meta['schema']=='samurai-usb-irq-protection-rollback-restart-v1' and
  re.fullmatch(r'usb-irq-protection-rollback-activate-[a-z0-9-]{8,48}',meta['transaction_id']) and
  re.fullmatch('[0-9a-f]{48}',meta['token']),'new rollback restart identity')
 need(meta['transaction_id']!=meta['rollback']['transaction_id'] and guard_path.parent==ROOT/meta['transaction_id'],'independent restart directory')
 need(meta['kernel_release']==RELEASE and meta['kernel_version']==VERSION and meta['partitions']==['boot'] and
  meta['rollback_boot_sha256']==BOOT and meta['unchanged_logdump_sha256']==LOGDUMP and
  meta['boot_bytes']==100663296 and meta['logdump_bytes']==67108864 and
  meta['disk_state']=='all_original_fsynced' and meta['runtime_validation_accepted'] is False,'fixed rollback target and pending runtime')
 need(set(meta['post_restore_probe'])=={'stdin_sha256','stdout_sha256','child_sha256','terminal_sha256'} and
  all(re.fullmatch('[0-9a-f]{64}',v) for v in meta['post_restore_probe'].values()),'actual post-restore probe digests')


def validate_activation_guard(guard_path,allow_inhibit=False):
 global OLD_NOTES
 need(os.geteuid()==0 and not sys.flags.optimize,'root nonoptimized worker')
 guard_path=secure_file(guard_path);meta=json.loads(raw_owned(guard_path));validate_meta_shape(meta,guard_path)
 owned_directory(guard_path.parent);acquire_service_lock()
 need(str(uuid.UUID(meta['boot_id']))==meta['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'same actual rollback boot')
 need(os.uname().machine=='aarch64' and os.uname().release==RELEASE and os.uname().version==VERSION,'only exact current Image502')
 need(Path('/proc/sys/kernel/tainted').read_text().strip()=='0','taint')
 need(file_sha('/etc/samurai-rootfs-release')==meta['rootfs_release_sha256'],'rootfs')
 serial=Path('/sys/devices/soc0/serial_number').read_bytes();compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
 need(serial.strip() and sha(serial)==meta['soc_serial_sha256'] and sha(compatible)==meta['compatible_sha256'] and
  b'realme,samurai' in compatible.split(b'\0'),'board identity')
 request,worker=rollback_material(meta)
 need(block_sha('/dev/disk/by-partlabel/boot',100663296)==meta['current_boot_sha256'] and
  block_sha('/dev/disk/by-partlabel/logdump',67108864)==LOGDUMP,'current complete carriers')
 need(file_sha('/usr/share/samurai-charging/manifest.json')==OLD,'restored original R8 manifest')
 manifest=json.loads(Path('/usr/share/samurai-charging/manifest.json').read_bytes())
 need(manifest==EXPECTED_MANIFEST,'exact restored R8 structure')
 for path,digest in manifest['installed_files'].items():need(file_sha(path)==digest,'original/retained installed file: '+path)
 for path,digest in OLD_FILES.items():need(sha(raw_owned(path))==digest,'actual original restored file')
 OLD_NOTES=dict(worker.expected_profile(request)[1])
 need(meta['resident_notes']==OLD_NOTES,'explicit still-resident profile')
 for name,digest in OLD_NOTES.items():
  node=Path('/sys/module',name.replace('-','_'))
  need(sha((node/'notes/.note.gnu.build-id').read_bytes())==digest and (node/'initstate').read_text().strip()=='live','actual resident profile')
 need(Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y' and
  not Path('/sys/module/samurai_usbin_init').exists(),'retained native provider/no helper')
 need(file_sha(STARTUP_PATH)==STARTUP_SHA and Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text().strip()=='500','startup/descriptor500')
 need(Path('/sys/module/bq27xxx_battery/parameters/samurai_instant_current').read_text().strip()=='Y' and
  [v for v in Path('/proc/cmdline').read_text().split() if v.startswith('bq27xxx_battery.samurai_instant_current=')]==['bq27xxx_battery.samurai_instant_current=1'],'instant current opt-in')
 eud_off_check();camera481_check(guard_path.parent/'camera481-expected-private.json')
 data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME))
 if not allow_inhibit:environment(data)
 phase=Path('/run')/(meta['transaction_id']+'-reboot-phase-private.json')
 need(not phase.exists(),'restart already claimed; retain original evidence')
 return meta,Path('/var/lib/samurai')/meta['transaction_id'],phase
