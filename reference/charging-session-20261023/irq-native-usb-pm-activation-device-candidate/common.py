"""Current cold-stage guards. Definitions have no device side effects."""
import base64,fcntl,hashlib,json,os,re,runpy,stat,struct,sys,time,uuid
from pathlib import Path
ROOT=Path('/root/charging-management-20261023')
SERVICE_LOCK='/run/lock/samurai-charging.lock'
STAGE_WORKER='8e188610e8002c4d23a70a7d3d01572366ebf668c0674ac93ea4f05b23aeb7e8'
STAGE_SUPERVISOR='b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'
LIVE_PATH='/usr/lib/samurai-charging/live-session.py'
LIVE_SHA='2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
_SERVICE_FD=None
_MAC_FD=None
CAMERA481='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
SENSOR468_NOTE='a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13'
FIXED={'schema': 'samurai-irq-native-usb-pm-activation-v1', 'kernel_release': '7.3.0-rc6-rmx1931-samurai-k363+', 'kernel_version': '#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'source_kernel_version': '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'partitions': ['logdump'], 'boot_bytes': 100663296, 'logdump_bytes': 67108864, 'image502_sha256': '085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955', 'charging_manifest_sha256': '34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b', 'source_manifest_sha256': '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5', 'cohort_delivery_sha256': '89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01', 'startup500_sha256': '2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a', 'startup500_path': '/usr/local/sbin/samurai-usb', 'max_power_ma': 500, 'camera481_expected_sha256': '1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705', 'new_disk_files': {'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037', '/usr/share/samurai-charging/manifest.json': '34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b'}, 'old_resident_notes': {'samurai_usb_input': 'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d', 'samurai_gauge_protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai_mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}, 'unchanged_boot_sha256': 'eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06', 'candidate_logdump_sha256': '4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83', 'rollback_logdump_sha256': 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1', 'image504_sha256': 'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4'}
EXPECTED_MANIFEST={'release': '7.3.0-rc6-rmx1931-samurai-k363+', 'modules': {'samurai-mp2650': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', 'sha256': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'}, 'samurai-usb-input': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', 'sha256': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'}, 'samurai-gauge-protection': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko', 'sha256': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}}, 'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000, 'source_budget_enforced': True, 'installed_files': {'/usr/sbin/samurai-charging': '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4', '/etc/init.d/samurai-charging': 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', '/usr/lib/samurai-charging/control-trial.py': 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761', '/usr/lib/samurai-charging/live-session.py': '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}, 'adapter_revision': 'usb-irq-native-pm-budget504-01'}
OLD_MANIFEST={'release': '7.3.0-rc6-rmx1931-samurai-k363+', 'modules': {'samurai-mp2650': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', 'sha256': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'}, 'samurai-usb-input': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', 'sha256': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'}, 'samurai-gauge-protection': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko', 'sha256': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}}, 'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000, 'source_budget_enforced': True, 'installed_files': {'/usr/sbin/samurai-charging': '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4', '/etc/init.d/samurai-charging': 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', '/usr/lib/samurai-charging/control-trial.py': 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761', '/usr/lib/samurai-charging/live-session.py': '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}, 'adapter_revision': 'usb-irq-protection-observer-01'}
RELEASE='7.3.0-rc6-rmx1931-samurai-k363+'
VERSION='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
LOGDUMP='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
OLD='18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'
OLD_NOTES={'samurai-usb-input': 'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d', 'samurai-gauge-protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai-mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}
USB='/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko'
MANIFEST='/usr/share/samurai-charging/manifest.json'
OLD_FILES={'/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f', '/usr/share/samurai-charging/manifest.json': '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5'}
PAYLOAD='f1162d2b5614327f0ce78c918cec62fd681d42cca99d8c03819cfa41086230bc'
MAC_CACHE_SHA='02c98143301bb5db896c6f535f490495428df8b8c6fd6ab3cdc69ca507a545a8'

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

def stage_paths(transaction):
 need(re.fullmatch(r'irq-native-usb-pm-stage-[a-z0-9-]{8,48}',transaction),'current cold stage name')
 root=ROOT/transaction;out=root/'device-stage'
 return {**{k:str(root/v) for k,v in {
  'request':'request-private.json','worker_launch':'worker-launch-receipt-private.json',
  'worker_terminal':'worker-terminal-private.json','supervisor_launch':'launch-receipt-private.json',
  'supervisor_process':'supervisor-process-private.json','supervisor_terminal':'supervisor-terminal-private.json',
  'worker_source':'stage-worker.py','supervisor_source':'stage-supervisor.py'}.items()},
  **{k:str(out/v) for k,v in {'device_request':'request-private.json','result':'result.json',
  'before':'before-private.json','stopped':'stopped-private.json','after':'after-private.json',
  'worker_process':'process-private.json','files_before':'files-before-private.json',
  'old_usb':'samurai-usb-input.ko.before','old_manifest':'manifest.json.before'}.items()}}

def validate_stage_receipts(meta,records,processes):
 stage=meta['stage'];tx=stage['transaction_id'];paths=stage_paths(tx)
 need(set(stage)=={'transaction_id','request_sha256','result_sha256','host_binding_sha256',
  'worker_sha256','supervisor_sha256','evidence'},'stage exact fields')
 need(stage['worker_sha256']==STAGE_WORKER and stage['supervisor_sha256']==STAGE_SUPERVISOR,'fixed original stage sources')
 need(set(stage['evidence'])==set(paths),'stage evidence keys')
 for key,path in paths.items():
  item=stage['evidence'][key]
  need(set(item)=={'path','sha256'} and item['path']==path and re.fullmatch('[0-9a-f]{64}',item['sha256']),'fixed original evidence path/hash')
 for name in ['request_sha256','result_sha256','host_binding_sha256']:
  need(re.fullmatch('[0-9a-f]{64}',stage[name]),'actual stage digest: '+name)
 need(stage['evidence']['request']['sha256']==stage['evidence']['device_request']['sha256']==stage['request_sha256'] and
  stage['evidence']['result']['sha256']==stage['result_sha256'],'executed request/result raw binding')
 need(stage['evidence']['worker_source']['sha256']==STAGE_WORKER and stage['evidence']['supervisor_source']['sha256']==STAGE_SUPERVISOR,'source evidence hashes')
 req=records['request'];result=records['result'];w=records['worker_process'];s=records['supervisor_process']
 need(req==records['device_request'] and set(req)=={'schema','transaction_id','cohort_delivery_sha256','payload_sha256','payload_base64',
  'worker_sha256','identity','adoption','lease_token'},'original exact executed request')
 need(req['schema']=='samurai-irq-native-usb-pm-stage-request-v1' and req['transaction_id']==tx and req['worker_sha256']==STAGE_WORKER,'current stage request')
 payload=base64.b64decode(req['payload_base64'],validate=True)
 need(req['cohort_delivery_sha256']==FIXED['cohort_delivery_sha256'] and req['payload_sha256']==PAYLOAD and
  len(payload)==27163 and sha(payload)==PAYLOAD and re.fullmatch('[0-9a-f]{48}',req['lease_token']),'actual current cohort/payload')
 identity=dict(boot_id=meta['boot_id'],version=FIXED['source_kernel_version'],serial_sha256=meta['soc_serial_sha256'],
  compatible_sha256=meta['compatible_sha256'],rootfs_sha256=meta['rootfs_release_sha256'])
 need(req['identity']==identity and req['adoption']==meta['adoption'],'same actual source boot/guard')
 need(result['schema']=='samurai-irq-native-usb-pm-stage-result-v1' and result['transaction_id']==tx and
  result['request_sha256']==stage['request_sha256'] and result['cohort_delivery_sha256']==FIXED['cohort_delivery_sha256'] and
  result['payload_sha256']==PAYLOAD,'stage result binding')
 need(result['terminal'] is True and result['staged'] is True and result['phase']=='staged' and
  result['status']=='staged/runtime_pending' and result['runtime_pending'] is True and
  result['disk_state']=='all_new_fsynced' and result['stop_verified'] is True,'complete current stage terminal')
 need(all(result.get(k) is None for k in ['primary_error','stop_error','recovery_error','receipt_error','close_error']) and
  result.get('restored_original_disk') is not True,'no failed/restored stage promotion')
 need(all(result.get(k) is False for k in ['activation_attempted','new_module_loaded','capture_issued']),'no stage activation')
 need(result['old_manifest_sha256']==FIXED['source_manifest_sha256'] and result['new_manifest_sha256']==FIXED['charging_manifest_sha256'] and
  result['resident_notes']==OLD_NOTES,'old live/current disk tuple')
 need(set(result['final_files'])==set(FIXED['new_disk_files']),'exact two final disk files')
 for name,digest in FIXED['new_disk_files'].items():
  need(result['final_files'][name]==dict(sha256=digest,mode='0o600',classification='new'),'actual stage final readback')
 temporary={str(Path(name).with_name('.'+Path(name).name+'.'+tx+suffix+'.next')) for name in FIXED['new_disk_files'] for suffix in ('','-restore')}
 need(set(result['temporary_files'])==temporary and all(v=={'state':'absent'} for v in result['temporary_files'].values()),'no unknown/retained atomic temporary')
 need(sha(records['old_usb'])==OLD_FILES[USB] and sha(records['old_manifest'])==OLD and
  json.loads(records['old_manifest'])==OLD_MANIFEST,'actual exact old disk backups')
 need(records['files_before']=={USB:dict(sha256=OLD_FILES[USB],mode='0600',bytes=len(records['old_usb'])),
  MANIFEST:dict(sha256=OLD,mode='0600',bytes=len(records['old_manifest']))},'actual two-file backup metadata')
 before,paused,after=[records[n] for n in ['before','stopped','after']]
 for snapshot in [before,paused,after]:
  need(snapshot['identity']==dict(identity,guard_sha256=meta['adoption']['guard_sha256']) and snapshot['notes']==OLD_NOTES,'stage snapshot identity/live tuple')
  safe_sample(snapshot,snapshot['read_end'])
  need(snapshot['source']==before['source'] and snapshot['limits']==before['limits'] and
   all(snapshot['state'][k]==before['state'][k] for k in ['boot_id','release','camera_pm','m2m','services','driver','taint']) and
   snapshot['state']['registers']==snapshot['registers'],'stage source/limits/environment retained')
  need(snapshot['mac_evidence']==before['mac_evidence'],'same consumed MAC instance/cache')
 environment(before)
 need(charging_sample_phase(before['sample']) and before['registers']['08']&0x18==(0 if before['sample']['logical_full'] else 0x10),'healthy managed or real Full before stop')
 for previous,current in [(before,paused),(paused,after)]:
  need(previous['read_end']<=current['read_start'] and charging_sample_phase(current['sample'],True) and
   current['registers']['08']==(previous['registers']['08']&~0x18)|8 and current['registers']['13']&2,'ordered synchronous INHIBIT samples')
  need(set(previous['registers'])==set(current['registers']) and '14' not in current['registers'] and
   all(current['registers'][k]==v for k,v in previous['registers'].items() if k not in ['08','13']),'retained non-destructive configuration')
  if previous['sample']['logical_full']:
   need(current['sample']['logical_full']==1 and current['sample']['full_cause']==previous['sample']['full_cause'] and current['sample']['session_seconds']==0,'logical Full/cause retained through stop and stage')
 need(result['logical_full_retained']==after['sample']['logical_full'] and result['full_cause_retained']==after['sample']['full_cause'],'final Full result/sample binding')
 wargv=['python3','-B',str(ROOT/tx/'stage-worker.py'),'--execute-stage']
 sargv=['python3','-B',str(ROOT/tx/'stage-supervisor.py'),'--execute-supervisor']
 need(set(w)=={'transaction_id','boot_id','pid','start_ticks','argv'},'actual five-field stage self receipt')
 for receipt,argv in [(w,wargv),(s,sargv)]:
  need(type(receipt['pid']) is int and receipt['pid']>0 and type(receipt['start_ticks']) is int and receipt['start_ticks']>0 and
   receipt['transaction_id']==tx and receipt['boot_id']==meta['boot_id'] and receipt['argv']==argv,'original process instance')
 need(s['request_sha256']==stage['request_sha256'],'supervisor original request')
 wl,wt,sl,st=[records[k] for k in ['worker_launch','worker_terminal','supervisor_launch','supervisor_terminal']]
 for item,pid,argv in [(wl,w['pid'],wargv),(wt,w['pid'],wargv),(sl,s['pid'],sargv),(st,s['pid'],sargv)]:
  need(item['pid']==pid and item['argv']==argv and item['transaction_id']==tx and item['boot_id']==meta['boot_id'] and
   item['request_sha256']==stage['request_sha256'],'same original child/request')
 need(wl['supervisor_pid']==wt['supervisor_pid']==s['pid'] and wl.get('start_ticks') in [None,w['start_ticks']] and
  sl.get('start_ticks') in [None,s['start_ticks']] and st['start_ticks']==s['start_ticks'],'original child ownership/instances')
 need(wt['terminal'] is True and type(wt['returncode']) is int and wt['returncode']==0 and
  st['terminal'] is True and type(st['returncode']) is int and st['returncode']==0 and
  st['worker_pid']==w['pid'] and type(st['worker_returncode']) is int and st['worker_returncode']==0,'both original Popen wait0')
 for key,receipt in [('worker',w),('supervisor',s)]:
  observed=processes[key]
  need(observed['pid']==receipt['pid'] and observed['state'] in ['absent','zombie'],'original process not alive/unknown/reused')
  if observed['state']=='zombie':need(observed['start_ticks']==receipt['start_ticks'],'same zombie instance')
 return req

def validate_stage_records(meta,records,processes,claim):
 request=validate_stage_receipts(meta,records,processes)
 tx=meta['stage']['transaction_id'];root=ROOT/tx
 need(claim['transaction_id']==tx and claim['boot_id']==meta['boot_id'] and claim['request_sha256']==meta['stage']['request_sha256'] and
  claim['request_count']==1 and claim['argv']==['python3','-B',str(root/'stage-worker.py'),'--execute-stage'] and
  claim['supervisor_argv']==['python3','-B',str(root/'stage-supervisor.py'),'--execute-supervisor'] and
  claim['supervisor_sha256']==STAGE_SUPERVISOR,'original device launch claim')
 return request

def read_stage(meta):
 stage=meta['stage'];root=owned_directory(ROOT/stage['transaction_id']);owned_directory(root/'device-stage');records={}
 for key,path in stage_paths(stage['transaction_id']).items():
  item=stage['evidence'][key];need(item['path']==path,'original stage path')
  raw=raw_owned(path);need(sha(raw)==item['sha256'],'stage original bytes changed: '+key)
  if key not in ['worker_source','supervisor_source']:
   records[key]=raw if key in ['old_usb','old_manifest'] else json.loads(raw)
 processes={k:process_observation(records[k+'_process']) for k in ['worker','supervisor']}
 claim=json.loads(raw_owned(root/'launch-claim-private.json'))
 validate_stage_records(meta,records,processes,claim)
 return records

def verify_consumed_cache(expected):
 global _MAC_FD
 instance=Path('/sys/devices/platform/samurai-gauge-protection');attribute=instance/'mac_evidence'
 need((instance/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','same bound protection driver')
 if _MAC_FD is None:_MAC_FD=os.open(attribute,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
 held,current=os.fstat(_MAC_FD),attribute.stat()
 need((held.st_dev,held.st_ino)==(current.st_dev,current.st_ino)==(expected['attribute_dev'],expected['attribute_inode']) and
  instance.stat().st_ino==expected['instance_inode'],'same already-consumed protection instance')
 os.lseek(_MAC_FD,0,os.SEEK_SET);raw=os.read(_MAC_FD,16384)
 need(0<len(raw)<16384 and raw.endswith(b'\n') and sha(raw)==MAC_CACHE_SHA==expected['sha256'] and
  base64.b64encode(raw).decode()==expected['raw_base64'],'same original consumed MAC report bytes')
 first=dict(x.split('=',1) for x in raw.decode().splitlines()[0].split())
 need(first.get('attempted')==first.get('terminal')=='1','no new MAC capture')

def validate_meta_shape(meta,guard_path):
 need(guard_path.is_absolute() and guard_path.name=='guard-private.json','private guard path')
 need(set(meta)==set(FIXED)|{'transaction_id','token','boot_id','soc_serial_sha256','compatible_sha256',
  'rootfs_release_sha256','adoption','stage'},'exact activation fields')
 need(all(meta.get(k)==v for k,v in FIXED.items()),'current fixed activation profile')
 need(re.fullmatch(r'irq-native-usb-pm-activate-[a-z0-9-]{8,48}',meta['transaction_id']) and
  re.fullmatch('[0-9a-f]{32,64}',meta['token']),'new independent activation')
 need(guard_path.parent==ROOT/meta['transaction_id'],'new activation directory')


def validate_activation_guard(guard_path,allow_inhibit=False):
 need(os.geteuid()==0 and not sys.flags.optimize,'root non-optimized worker')
 guard_path=secure_file(guard_path);meta=json.loads(raw_owned(guard_path))
 validate_meta_shape(meta,guard_path)
 owned_directory(guard_path.parent);acquire_service_lock()
 need(str(uuid.UUID(meta['boot_id']))==meta['boot_id'] and meta['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'actual original #502 boot')
 need(os.uname().machine=='aarch64' and os.uname().release==FIXED['kernel_release'] and os.uname().version==FIXED['source_kernel_version'],'exact adopted Image502')
 need(Path('/proc/sys/kernel/tainted').read_text().strip()=='0','taint')
 need(file_sha('/etc/samurai-rootfs-release')==meta['rootfs_release_sha256'],'rootfs')
 serial=Path('/sys/devices/soc0/serial_number').read_bytes();compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
 need(serial.strip() and sha(serial)==meta['soc_serial_sha256'] and sha(compatible)==meta['compatible_sha256'] and b'realme,samurai' in compatible.split(b'\0'),'board identity')
 adoption=meta['adoption'];need(set(adoption)=={'transaction_id','guard_path','guard_sha256'},'actual IRQ adoption fields')
 need(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}',adoption['transaction_id']) and
  adoption['guard_path']=='/var/lib/samurai/'+adoption['transaction_id']+'-adopted/boot-id-private.txt' and
  re.fullmatch('[0-9a-f]{64}',adoption['guard_sha256']),'actual source IRQ adopted guard')
 owned_directory(Path(adoption['guard_path']).parent)
 guard=raw_owned(adoption['guard_path']);need(guard==(meta['boot_id']+'\n').encode() and sha(guard)==adoption['guard_sha256'],'actual adopted guard bytes')
 records=read_stage(meta)
 need(block_sha('/dev/disk/by-partlabel/boot',100663296)==FIXED['unchanged_boot_sha256'] and
  block_sha('/dev/disk/by-partlabel/logdump',67108864)==FIXED['rollback_logdump_sha256'],'current complete carriers read-only')
 need(file_sha('/usr/share/samurai-charging/manifest.json')==FIXED['charging_manifest_sha256'],'new staged disk manifest')
 manifest=json.loads(Path('/usr/share/samurai-charging/manifest.json').read_bytes())
 need(manifest==EXPECTED_MANIFEST,'exact new manifest structure')
 for path,digest in manifest['installed_files'].items():need(file_sha(path)==digest,'current retained/new file: '+path)
 for path,digest in FIXED['new_disk_files'].items():need(sha(raw_owned(path))==digest,'two actual new disk files')
 for name,digest in FIXED['old_resident_notes'].items():
  need(sha(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes())==digest and Path('/sys/module',name,'initstate').read_text().strip()=='live','old live note independent of new disk')
 need(Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y' and not Path('/sys/module/samurai_usbin_init').exists(),'native provider retained/no helper')
 need(file_sha(FIXED['startup500_path'])==FIXED['startup500_sha256'] and Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text().strip()=='500','startup/descriptor500')
 need(Path('/sys/module/bq27xxx_battery/parameters/samurai_instant_current').read_text().strip()=='Y' and
  [x for x in Path('/proc/cmdline').read_text().split() if x.startswith('bq27xxx_battery.samurai_instant_current=')]==['bq27xxx_battery.samurai_instant_current=1'],'current gauge opt-in')
 eud_off_check();camera481_check(guard_path.parent/'camera481-expected-private.json')
 verify_consumed_cache(records['after']['mac_evidence'])
 data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME))
 verify_consumed_cache(records['after']['mac_evidence'])
 if not allow_inhibit:environment(data)
 phase=Path('/run')/(meta['transaction_id']+'-reboot-phase-private.json');need(not phase.exists(),'restart already claimed; inspect original only')
 return meta,Path('/var/lib/samurai')/meta['transaction_id'],phase
