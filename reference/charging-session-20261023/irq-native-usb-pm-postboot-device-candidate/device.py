"""Read-only named IRQ/OF evidence. Counts alone do not establish causality."""
from pathlib import Path
import base64
import re
import struct
import time

NAMES = ('usbin-plugin', 'usbin-src-change')
NODE = '/sys/firmware/devicetree/base/soc@0/spmi@c440000/pmic@2/usb-input@1300'
PROPERTIES = {'compatible': b'realme,rmx1931-usb-input\0', 'reg': struct.pack('>I', 0x1300),
              'interrupts': struct.pack('>8I', 2, 0x13, 4, 3, 2, 0x13, 6, 1),
              'interrupt-names': b'usbin-plugin\0usbin-src-change\0', 'status': b'okay\0'}


def parse_interrupts(text):
    if not isinstance(text, str):
        raise ValueError('unreadable /proc/interrupts')
    lines = text.splitlines()
    if not lines:
        raise ValueError('missing CPU header')
    cpus = lines[0].split()
    if not cpus or len(cpus) > 256 or len(set(cpus)) != len(cpus) or not all(re.fullmatch(r'CPU[0-9]+', c) for c in cpus):
        raise ValueError('invalid CPU header')
    found = {}
    for line in lines[1:]:
        match = re.match(r'^\s*([0-9]+):\s+(.*)$', line)
        if not match:
            continue
        columns = match[2].split()
        mentioned = [name for name in NAMES if name in re.split(r'[\s,]+', match[2])]
        if not mentioned:
            continue
        if len(mentioned) != 1:
            raise ValueError('ambiguous/shared named IRQ')
        name = mentioned[0]
        if name in found or len(columns) <= len(cpus) or ',' in match[2] or columns[-1] != name:
            raise ValueError('ambiguous/shared named IRQ')
        counts = columns[:len(cpus)]
        if not all(re.fullmatch(r'[0-9]+', count) for count in counts):
            raise ValueError('invalid per-CPU IRQ count')
        if not 0 < int(match[1]) < (1 << 31) or any(int(count) >= (1 << 64) for count in counts):
            raise ValueError('out-of-range IRQ or counter')
        found[name] = {'irq': int(match[1]), 'counts': dict(zip(cpus, map(int, counts))),
                       'controller_and_action': ' '.join(columns[len(cpus):]), 'raw_line': line}
    if set(found) != set(NAMES) or len({r['irq'] for r in found.values()}) != 2:
        raise ValueError('both unique named IRQ registrations required; polling is insufficient')
    return {'cpus': cpus, 'named': found}


def snapshot():
    started = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    device = Path('/sys/class/power_supply/samurai-usb-input/device').resolve(strict=True)
    providers = []
    for path in Path('/sys/bus/platform/devices').iterdir():
        driver = path / 'driver'
        if driver.is_symlink() and driver.resolve(strict=True).name == 'samurai-usb-input':
            providers.append(str(path.resolve(strict=True)))
    result = {'started_boottime_ns': started,
            'device': str(device), 'driver': (device / 'driver').resolve(strict=True).name,
            'of_node': str((device / 'of_node').resolve(strict=True)), 'bound_providers': sorted(providers),
            'properties_b64': {name: base64.b64encode((Path(NODE) / name).read_bytes()).decode()
                               for name in PROPERTIES},
            'proc_interrupts': Path('/proc/interrupts').read_text()}
    result['ended_boottime_ns'] = time.clock_gettime_ns(time.CLOCK_BOOTTIME)
    return result


def validate_snapshot(raw):
    if not (isinstance(raw, dict) and raw.get('driver') == 'samurai-usb-input' and raw.get('of_node') == NODE):
        raise ValueError('supply must use the real native OF provider')
    if not isinstance(raw.get('device'), str) or not raw['device'].startswith('/sys/devices/') or raw.get('bound_providers') != [raw['device']]:
        raise ValueError('duplicate/missing bound USB provider')
    if not (0 <= raw['started_boottime_ns'] <= raw['ended_boottime_ns']):
        raise ValueError('invalid IRQ evidence interval')
    if set(raw['properties_b64']) != set(PROPERTIES):
        raise ValueError('missing native IRQ properties')
    for name, expected in PROPERTIES.items():
        if base64.b64decode(raw['properties_b64'][name], validate=True) != expected:
            raise ValueError('wrong OEM IRQ property: ' + name)
    return parse_interrupts(raw['proc_interrupts'])


def delta(before, after):
    a, b = validate_snapshot(before), validate_snapshot(after)
    result = {'comparable': False, 'positive_counts': {}, 'physical_delivery_accepted': False}
    if before['device'] != after['device'] or before['of_node'] != after['of_node']:
        return dict(result, reason='provider changed')
    if after['started_boottime_ns'] < before['ended_boottime_ns']:
        return dict(result, reason='intervals overlap or reverse')
    if a['cpus'] != b['cpus']:
        return dict(result, reason='online CPU set changed; totals cannot be compared')
    increments = {}
    for name in NAMES:
        old, new = a['named'][name], b['named'][name]
        if old['irq'] != new['irq']:
            return dict(result, reason='Linux IRQ mapping changed')
        values = {cpu: new['counts'][cpu] - old['counts'][cpu] for cpu in a['cpus']}
        if any(value < 0 for value in values.values()):
            return dict(result, reason='per-CPU counter regressed')
        increments[name] = {'irq': new['irq'], 'per_cpu': values, 'sum': sum(values.values())}
    return dict(result, comparable=True, reason=None, increments=increments,
                positive_counts={name: item['sum'] > 0 for name, item in increments.items()})


def check_postboot(raw):
    first, last = raw['irq_before'], raw['irq_after']
    a, b = validate_snapshot(first), validate_snapshot(last)
    if first['device'] != last['device'] or any(a['named'][n]['irq'] != b['named'][n]['irq'] for n in NAMES):
        raise ValueError('provider/IRQ instance changed during postboot collection')
    if not (raw['started_boottime_ns'] <= first['started_boottime_ns'] <= first['ended_boottime_ns']
            <= last['started_boottime_ns'] <= last['ended_boottime_ns'] <= raw['ended_boottime_ns']):
        raise ValueError('IRQ snapshots outside collection interval')
    return {'native_OF_provider_and_exact_IRQ_properties': True, 'both_named_IRQs_registered': True,
            'Linux_IRQs': {name: b['named'][name]['irq'] for name in NAMES},
            'interval_delta': delta(first, last), 'IRQ_delivery_or_icon_latency_accepted': False}


"""One-shot postboot reads only. Default --check-local never collects.
No SSH implementation, guard adoption, CSR access or automatic recovery.
"""
from pathlib import Path
import argparse,base64,fcntl,hashlib,json,os,re,stat,struct,subprocess,sys,time
sha=lambda raw:hashlib.sha256(raw).hexdigest()
IRQ_BOOT='eddadec33fcd1d114c45af76cb9fc6d6b5f1de2c81c0e9fada099c5b884f6e06'
IMAGE502='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'
LOGDUMP502='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
CAMERA481='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
COHORT_MANIFEST='5fca8e5a0795325bd780b7965579068c7edc35fa7da12bac357bb30bbde69417'
COHORT_EXPECTED_MANIFEST=json.loads('{\n  "release": "7.3.0-rc6-rmx1931-samurai-k363+",\n  "modules": {\n    "samurai-mp2650": {\n      "target": "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko",\n      "sha256": "10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f"\n    },\n    "samurai-usb-input": {\n      "target": "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko",\n      "sha256": "7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f"\n    },\n    "samurai-gauge-protection": {\n      "target": "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko",\n      "sha256": "7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044"\n    }\n  },\n  "default_input_cap_ua": 900000,\n  "default_charge_cap_ua": 250000,\n  "source_budget_enforced": true,\n  "installed_files": {\n    "/usr/sbin/samurai-charging": "61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4",\n    "/etc/init.d/samurai-charging": "bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a",\n    "/usr/lib/samurai-charging/control-trial.py": "c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761",\n    "/usr/lib/samurai-charging/live-session.py": "2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b",\n    "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko": "10ec06fb9d798d72e08495617cfc04e7e49c77e536a12f205053e9cdbfa6297f",\n    "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko": "7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f",\n    "/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko": "7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044"\n  },\n  "adapter_revision": "usb-irq-protection-observer-01"\n}\n')
COHORT_NOTES={'samurai_usb_input':'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d',
 'samurai_gauge_protection':'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec',
 'samurai_mp2650':'f4d5768a4250b901ea956560d9c6b4b1dd32ac80893cbbd31609d9c032c4680d'}
SENSOR468_NOTE='a52ef87a2388757c542768e5438120d858e785bd334c080b55dec0f532c54d13'

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


def check_file(f,digest):
 assert f['sha256']==digest and f['regular'] and not f['symlink']
 assert f['uid']==0 and not f['mode']&0o022



PM=['ac10000.icp','acb3000.camss','ac4a000.cci','ac4b000.cci']
SERVICES=['phoc','phosh','pipewire','wireplumber']
FAULTS=['WARNING:','Oops:','refcount_t: underflow','gpu fault:','NGD resume failed',
        'fatal error received','Unhandled context fault:','Kernel panic - not syncing',
        'Unable to handle kernel','cannot create duplicate filename']
BANDS=[(-20,0,250000,3980000,3990000),(0,50,900000,4400000,4410000),
       (50,120,1100000,4400000,4410000),(120,160,1100000,4400000,4410000),
       (160,440,1100000,4400000,4410000),(440,530,550000,4130000,4140000)]

def block_fact(path,length):
 fd=os.open(path,os.O_RDONLY|os.O_CLOEXEC)
 try:
  assert stat.S_ISBLK(os.fstat(fd).st_mode)
  size=struct.unpack('=Q',fcntl.ioctl(fd,0x80081272,bytes(8)))[0]
  assert size==length,'partition length mismatch'
  digest=hashlib.sha256();remaining=length
  while remaining:
   data=os.read(fd,min(1048576,remaining));assert data,'short partition read'
   digest.update(data);remaining-=len(data)
  return {'path':path,'bytes':size,'sha256':digest.hexdigest(),'open_mode':'O_RDONLY'}
 finally:os.close(fd)

def identity():
 return {'boot_id':read('/proc/sys/kernel/random/boot_id'),
  'uname':dict(zip(['sysname','nodename','release','version','machine'],os.uname())),
  'rootfs':attempt(lambda:file_fact('/etc/samurai-rootfs-release')),
  'serial_sha256':attempt(lambda:sha(Path('/sys/devices/soc0/serial_number').read_bytes())),
  'compatible_b64':attempt(lambda:base64.b64encode(Path('/sys/firmware/devicetree/base/compatible').read_bytes()).decode()),
  'taint':read('/proc/sys/kernel/tainted')}

def check_identity(r,g):
 assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',r['boot_id'])
 assert r['boot_id']!=g['boot_id'],'still old boot'
 assert r['boot_id']==g['new_boot_id'],'exact fresh-probed new boot'
 assert r['uname']['machine']=='aarch64' and r['taint']=='0'
 assert r['uname']['release']==g['kernel_release']=='7.3.0-rc6-rmx1931-samurai-k363+'
 assert r['uname']['version']==g['target_kernel_version']==EXPECTED_VERSION
 check_file(r['rootfs'],g['rootfs_release_sha256'])
 assert r['serial_sha256']==g['soc_serial_sha256']
 compatible=base64.b64decode(r['compatible_b64'],validate=True)
 assert sha(compatible)==g['compatible_sha256'] and b'realme,samurai' in compatible.split(b'\0')
 return {'new_boot':True,'same_board_release_rootfs_target_kernel':True}

def service_facts():
 result={name:[] for name in SERVICES}
 for p in Path('/proc').glob('[0-9]*'):
  try:
   comm=(p/'comm').read_text().strip()
   if comm not in result:continue
   fields=(p/'stat').read_text().rsplit(')',1)[1].split()
   if fields[0]=='Z':continue
   uid=int(re.search(r'^Uid:\s+(\d+)',(p/'status').read_text(),re.M)[1])
   result[comm].append({'pid':int(p.name),'start_ticks':fields[19],'state':fields[0],
     'uid':uid,'exe':os.readlink(p/'exe'),
     'cmdline_b64':base64.b64encode((p/'cmdline').read_bytes()).decode()})
  except (OSError,AttributeError,IndexError):continue
 return result

def eud_facts():
 dt=Path('/sys/firmware/devicetree/base')
 nodes=[]
 for p in dt.rglob('compatible'):
  try:
   if b'qcom,sm8150-eud-com' in p.read_bytes().split(b'\0'):
    nodes.append({'node':str(p.parent),'compatible_b64':base64.b64encode(p.read_bytes()).decode(),
                  'status':read(p.parent/'status')})
  except OSError:continue
 devices=[]
 for p in Path('/sys/bus/platform/devices').glob('*'):
  try:
   if (p/'driver').exists() and (p/'driver').resolve().name=='qcom_eud_com':devices.append(p.name)
  except OSError:continue
 return {'dt_com_nodes':nodes,'cmdline':read('/proc/cmdline'),
   'chosen_bootargs':read(dt/'chosen/bootargs'), 'chosen_stdout_path':read(dt/'chosen/stdout-path'),
   'bound_com_devices':devices,'tty_devices':[p.name for p in Path('/sys/class/tty').glob('*EUD*')],
   'proc_consoles':read('/proc/consoles'),'active_console':read('/sys/class/tty/console/active')}

def collect_base(request,raw=None):
 if raw is None:raw={}
 raw.update(identity_before=identity(),started_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))
 # No partition or RAM mapping before actual new-boot/board/kernel/rootfs match.
 initial=attempt(lambda:check_identity(raw['identity_before'],request['guard']))
 raw['identity_gate']=initial
 if 'error' in initial:return raw
 raw['irq_before']=attempt(snapshot)
 raw['boot_partition']=attempt(lambda:block_fact('/dev/disk/by-partlabel/boot',100663296))
 raw['logdump_partition']=attempt(lambda:block_fact('/dev/disk/by-partlabel/logdump',67108864))
 raw['manifest']=attempt(lambda:file_fact('/usr/share/samurai-charging/manifest.json'))
 raw['manifest_text']=read('/usr/share/samurai-charging/manifest.json')
 manifest=attempt(lambda:json.loads(raw['manifest_text']))
 raw['installed_files']={p:attempt(lambda p=p:file_fact(p)) for p in manifest.get('installed_files',{})}
 raw['charging_modules']={n:attempt(lambda n=n,info=info:module_fact(n.replace('-','_'),info['target']))
                           for n,info in manifest.get('modules',{}).items()}
 raw['charging_module_live']={n:read(Path('/sys/module',n.replace('-','_'),'initstate')) for n in manifest.get('modules',{})}
 raw['retained']=read('/sys/module/samurai_usb_input/parameters/native_retained')
 raw['helper_absent']=not Path('/sys/module/samurai_usbin_init').exists()
 ps=Path('/sys/class/power_supply');client=Path('/sys/bus/i2c/devices/0-005c')
 raw['telemetry_before']=read(client/'telemetry')
 raw['source']={n:read(ps/'samurai-usb-input'/n) for n in ['online','usb_type','current_max','input_current_limit']}
 raw['charger']={n:read(ps/'mp2650-input'/n) for n in ['status','health','online','charge_behaviour',
   'input_current_limit','constant_charge_current','constant_charge_voltage']}
 raw['protection_state']=read('/sys/devices/platform/samurai-gauge-protection/protection_state')
 raw['telemetry_after']=read(client/'telemetry')
 raw['udc']={p.name:{n:read(p/n) for n in ['state','current_speed']} for p in Path('/sys/class/udc').glob('*')}
 raw['config_max_power_ma']=read('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower')
 camera=request['camera']['expected']
 raw['camera_files']={p:attempt(lambda p=p:file_fact(p)) for p in camera['installed_files']}
 raw['camera_modules']={n:attempt(lambda n=n,info=info:module_fact(n,info['path'])) for n,info in camera['modules'].items()}
 raw['camera_module_live']={n:read(Path('/sys/module',n,'initstate')) for n in camera['modules']}
 raw['sensor_note']=attempt(lambda:sha(Path('/sys/module/s5k3m5/notes/.note.gnu.build-id').read_bytes()))
 raw['sensor_live']=read('/sys/module/s5k3m5/initstate')
 raw['package_db']=read('/lib/apk/db/installed')
 cam=Path('/sys/bus/platform/devices/ac10000.icp')
 raw['m2m']=read(cam/'m2m_status');raw['core']=read(cam/'state')
 raw['pm']={n:read(Path('/sys/bus/platform/devices')/n/'power/runtime_status') for n in PM}
 raw['user_services']=service_facts();raw['rc_status']=command(['rc-status','--all'])
 raw['remoteprocs']={p.name:{'name':read(p/'name'),'state':read(p/'state')} for p in Path('/sys/class/remoteproc').glob('*')}
 raw['hci0_present']=Path('/sys/class/bluetooth/hci0').exists()
 raw['eud']=eud_facts()
 raw['gauge']={'flag':read('/sys/module/bq27xxx_battery/parameters/samurai_instant_current'),
   'status':read(ps/'bq28z610-0/status'),'current_now':read(ps/'bq28z610-0/current_now'),
   'current_avg':read(ps/'bq28z610-0/current_avg')}
 raw['startup']=attempt(lambda:file_fact('/usr/local/sbin/samurai-usb'))
 raw['dmesg']=command(['dmesg'])
 raw['irq_after']=attempt(snapshot)
 raw['identity_after']=identity();raw['ended_boottime_ns']=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
 return raw

def check_partitions(r):
 assert r['boot_partition']['bytes']==100663296 and r['boot_partition']['sha256']==IRQ_BOOT
 assert r['logdump_partition']['bytes']==67108864 and r['logdump_partition']['sha256']==EXPECTED_LOGDUMP
 return dict(bootedd_exact=True,logdump_exact=True,image_sha256=EXPECTED_IMAGE,
  Image_binding='exact complete FAT plus frozen incremental Image receipt')

def check_install(r):
 check_file(r['manifest'],COHORT_MANIFEST);m=json.loads(r['manifest_text'])
 assert m==COHORT_EXPECTED_MANIFEST,'exact cohort manifest fields required'
 assert m['adapter_revision']==EXPECTED_REVISION and m['release']==r['identity_before']['uname']['release']
 assert set(m['modules'])=={n.replace('_','-') for n in COHORT_NOTES}
 for p,digest in m['installed_files'].items():check_file(r['installed_files'][p],digest)
 for n,info in m['modules'].items():
  f=r['charging_modules'][n];check_file(f,info['sha256'])
  assert f['loaded_note_matches_disk'] and f['loaded_note_sha256']==COHORT_NOTES[n.replace('-','_')]
  assert f['intree']['exit']==0 and f['intree']['stdout'].strip()=='Y'
  assert r['charging_module_live'][n]=='live'
 assert r['retained']=='Y' and r['helper_absent']
 return {'cohort_disk_and_new_live_notes':True}

def healthy_charge_mode(s):
 full=(s.get('logical_full')==s.get('hold_requested')==s.get('full_holding')==1 and s.get('full_cause') in (1,2,3) and s.get('desired_enable')==0 and s.get('session_seconds')==0)
 mode=full if any(s.get(k,0) for k in ['logical_full','hold_requested','full_holding','full_cause']) else s.get('desired_enable')==1
 return bool(mode)

def check_charging(r):
 s,c=r['source'],r['charger'];kind=active(s['usb_type']) if isinstance(s['usb_type'],str) else None
 # Preserve read errors/ENODATA/unknown: no fallback value or assumed 100mA.
 if kind not in ['SDP','CDP','DCP','C'] or any(not isinstance(s[k],str) for k in s):
  return {'state':'waiting_source','source_type':kind,'ready':False}
 native=int(s['input_current_limit']);budget=int(s['current_max'])
 assert 0<=native<=500000
 assert (kind=='SDP' and 0<=budget==native<=500000) or (kind in ['CDP','DCP'] and budget==1500000) or (kind=='C' and budget in [1500000,3000000])
 if budget==0 or s['online']!='1' or c['online']!='1':return {'state':'waiting_source','ready':False,'source_type':kind,'budget_ua':budget,'native_ua':native}
 assert c['health']=='Good' and active(c['charge_behaviour'])=='auto'
 ilim,cc,cv=(int(c[k]) for k in ['input_current_limit','constant_charge_current','constant_charge_voltage'])
 assert 50000<=ilim<=min(900000,budget) and ilim%50000==0
 assert 200000<=cc<=250000 and cc%50000==0
 assert 7425000<=cv<=8725000 and (cv//2-3712500)%12500==0 and cv%2==0
 states=[]
 for key in ['telemetry_before','telemetry_after']:
  t=parse_kv(r[key]);assert all(t[k]==1 for k in ['valid','online','protection_ok'])
  assert all(t[k]==0 for k in ['shadow','fault','error','stop_error','latched','source_inhibit','thermal_inhibit','cycle_timeout','gauge_charge_stop'])
  assert 0<=t['age_ms']<=3000 and 0<=t['session_seconds']<36000 and t['budget_ua']==budget and not t['flags']&0xc000
  assert 2000000<=t['cell1_uv']<=4600000 and 2000000<=t['cell2_uv']<=4600000
  assert 4000000<=t['pack_uv']<=9200000 and abs(t['cell1_uv']+t['cell2_uv']-t['pack_uv'])<=200000
  assert t['thermal_band'] in range(6);band=BANDS[t['thermal_band']]
  assert band[0]-20<=t['temp_decic']<band[1]+20
  assert max(t['cell1_uv'],t['cell2_uv'])<=band[4] and cc<=band[2] and cv//2<=min(4362500,band[3])
  assert healthy_charge_mode(t),'inconsistent Full/normal state'
  if t['logical_full']:
   assert t['desired_enable']==0 and t['full_holding']==t['hold_requested']==1 and t['full_cause'] in [1,2,3]
   states.append('healthy_full_charge_only_hold')
  else:
   assert t['desired_enable']==1 and t['full_holding']==t['hold_requested']==0
   states.append('healthy_charge_enabled')
 p=parse_kv(r['protection_state']);assert p['id']==0x2719 and p['error']==p['safety']==p['pf']==0
 assert p['operation']&0x300==0x300 and not p['operation']&((1<<20)|(1<<16)|0x7c00)
 assert p['manufacturing']&0x18==0x18 and not p['manufacturing']&0x8006
 assert p['pf_enabled']==int(bool(p['manufacturing']&0x40))==0
 assert int(r['config_max_power_ma'])==500
 return {'ready':True,'state':states,'source_type':kind,'budget_ua':budget,'native_ua':native,
         'input_ua':ilim,'charge_ua':cc,'cv_pack_uv':cv,'pf_enabled_inherited':p['pf_enabled']}

def check_camera(r,expected):
 for p,digest in expected['installed_files'].items():check_file(r['camera_files'][p],digest)
 versions={}
 for block in r['package_db'].split('\n\n'):
  f=dict(line.split(':',1) for line in block.splitlines() if ':' in line)
  if f.get('P') in expected['packages']:versions[f['P']]=f.get('V')
 assert versions==expected['packages']
 for n,info in expected['modules'].items():
  f=r['camera_modules'][n];check_file(f,info['sha256'])
  assert f['loaded_note_matches_disk'] and f['loaded_note_sha256']==info['note']
  assert r['camera_module_live'][n]=='live'
 assert r['sensor_note']==SENSOR468_NOTE and r['sensor_live']=='live'
 m=json.loads(r['m2m']);c=json.loads(r['core'])
 assert m['registered'] is True
 assert not any(m[k] for k in ['users','running','fatal','pinned','orphans','failed','cancelled','first_error'])
 assert m['jobs']==m['completed']==m['direct_completed']
 # owner_refs is a retained registered-provider reference, not active work.
 assert not any(c[k] for k in ['backing_owned','cpu_enabled','irq_enabled','power_held','remaining_groups','remaining_domains','mapped_bytes','ipe_dma_pending','request_fw_mapped','imported_buffers','imported_bytes','watchdogs','protocol_errors','cleanup_error','pc_error'])
 assert all(r['pm'][n]=='suspended' for n in PM)
 assert all(len(r['user_services'][n])==1 and r['user_services'][n][0]['uid']==10000 for n in SERVICES)
 return {'camera481_files_packages_notes':True,'four_PM_and_m2m_idle':True,'four_new_boot_services':True}

def eud_token(text):
 assert isinstance(text,str)
 return any(token.lower().startswith('earlycon') or ('eud' in token.lower() and token.lower().startswith('console=')) for token in text.replace('\0',' ').split())

def check_producers(r):
 e=r['eud'];assert len(e['dt_com_nodes'])==1 and e['dt_com_nodes'][0]['status'].strip('\0')=='disabled'
 assert not eud_token(e['cmdline']) and not eud_token(e['chosen_bootargs'])
 assert not e['bound_com_devices'] and not e['tty_devices']
 assert 'eud' not in e['proc_consoles'].lower() and 'eud' not in e['active_console'].lower()
 stdout=e['chosen_stdout_path']
 assert not isinstance(stdout,str) or 'eud' not in stdout.lower()
 return {'DT_disabled_no_EUD_cmdline_or_active_producer':True,'CSR_MMIO_read':False}


def check_services(r):
 rc=r['rc_status'];assert rc['exit']==0
 text=re.sub(r'\x1b\[[0-9;]*m','',rc['stdout'])
 for name in ['samurai-charging','bluetooth','samurai-ssc','iio-sensor-proxy','greetd']:
  assert re.search(r'^\s*'+re.escape(name)+r'\s+\[\s*started(?:\s+[^]\r\n]*)?\]',text,re.M),name
 assert r['hci0_present']
 remote={x['name']:x['state'] for x in r['remoteprocs'].values()}
 assert all(remote[n]=='running' for n in ['modem','adsp','slpi'])
 assert r['dmesg']['exit']==0
 counts={s:r['dmesg']['stdout'].count(s) for s in FAULTS};assert not any(counts.values()),counts
 return {'services_and_remoteprocs_running':True,'fault_counts':counts}

def check_gauge(r):
 assert r['gauge']['flag']=='Y'
 tokens=r['eud']['cmdline'].split()
 actual=[t for t in tokens if t.startswith('bq27xxx_battery.samurai_instant_current=')]
 assert actual==['bq27xxx_battery.samurai_instant_current=1']
 assert r['gauge']['status'] in ('Charging','Discharging','Not charging','Full')
 for name in ('current_now','current_avg'):
  assert isinstance(r['gauge'][name],str) and abs(int(r['gauge'][name]))<=50000000
 check_file(r['startup'],'2a364e12d72229ef7b0ddfd7620d5ff434b97eaf93eb60899fd24a03b5b9a54a')
 assert int(r['config_max_power_ma'])==500
 assert r['udc']['a600000.usb']['state']=='configured'
 kind=active(r['source']['usb_type'])
 assert int(r['source']['input_current_limit'])==500000
 budget=int(r['source']['current_max']);hardware=int(r['charger']['input_current_limit'])
 if kind=='SDP':assert budget==hardware==500000
 elif kind=='CDP':assert budget==1500000 and 50000<=hardware<=900000 and hardware%50000==0
 else:raise AssertionError('this startup profile requires actual SDP or CDP')
 return {'flag_Y_and_exact_cmdline':True,'CURRENT_NOW_instant_CURRENT_AVG_separate':True,
         'startup500_descriptor_and_native500_preserved':True,
         'source_type':kind,'source_budget_ua':budget,'hardware_input_ua':hardware,
         'SDP_hardware500_observed':kind=='SDP','pixel_or_physical_latency_accepted':False}


def audit(r,request):
 validate_request(request)
 result={'passed':False,'checks':{},'errors':{},'read_only':True,'guard_created':False,'hardware_writes':0,
         'physical_route_or_icon_or_SDP500_accepted':False}
 checks=[('identity',lambda:check_identity(r['identity_before'],request['guard'])),
  ('partitions',lambda:check_partitions(r)),('cohort_install',lambda:check_install(r)),
  ('charging',lambda:check_charging(r)),('camera481',lambda:check_camera(r,request['camera']['expected'])),
  ('EUD_producers',lambda:check_producers(r)),('instant_gauge',lambda:check_gauge(r)),
  ('services_faults',lambda:check_services(r)),
  ('native_IRQ_registration',lambda:check_postboot(r)),
  ('protection_cache_instance',lambda:check_cache(r)),('native_system_pm_link',lambda:check_pm_topology(r,request)),
  ('identity_after',lambda:check_identity(r['identity_after'],request['guard']))]
 for name,fn in checks:
  value=attempt(fn)
  if isinstance(value,dict) and 'error' in value:result['errors'][name]=value
  else:result['checks'][name]=value
 same=r.get('identity_after',{}).get('boot_id')==r['identity_before']['boot_id']
 if not same:result['errors']['boot_changed_during_capture']={'error':'identity changed or end read unavailable'}
 result['passed']=len(result['checks'])==len(checks) and not result['errors'] and all(x.get('ready',True) for x in result['checks'].values())
 return result

def main(argv=None,request=None):
 if sys.flags.optimize:raise RuntimeError('optimized Python disables required checks')
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--check-local',action='store_true');p.add_argument('--execute',action='store_true')
 p.add_argument('--window-confirmed',action='store_true');p.add_argument('--new-endpoint');args=p.parse_args(argv)
 if not args.execute:
  print(json.dumps(dict(local_checks_passed=True,device_accessed=False,read_only=True)));return 0
 assert args.window_confirmed and args.new_endpoint and request is not None
 assert request['new_endpoint']==args.new_endpoint;validate_request(request)
 raw={}
 try:collect(request,raw);result=audit(raw,request)
 except Exception as error:result=dict(passed=False,read_only=True,collection_error=type(error).__name__,message=str(error))
 print(json.dumps(dict(schema=request['schema'],profile=request['profile'],transaction_id=request['guard']['transaction_id'],
  context_sha256=request['context_sha256'],guard_sha256=request['guard_sha256'],raw=raw,result=result)),flush=True)
 return 0 if result['passed'] else 1

PROFILES={'forward_504': {'version': '#504 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'image': 'f6477d01d029cec888cafa739db0336e570274e9a3c38d4d5233959dd218a3f4', 'logdump': '4453d46202f4446810c8f72524a034a28acf3695f59eb12dbde8cf530e356d83', 'manifest_sha256': '34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b', 'manifest': {'release': '7.3.0-rc6-rmx1931-samurai-k363+', 'modules': {'samurai-mp2650': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', 'sha256': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'}, 'samurai-usb-input': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', 'sha256': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037'}, 'samurai-gauge-protection': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko', 'sha256': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}}, 'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000, 'source_budget_enforced': True, 'installed_files': {'/usr/sbin/samurai-charging': '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4', '/etc/init.d/samurai-charging': 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', '/usr/lib/samurai-charging/control-trial.py': 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761', '/usr/lib/samurai-charging/live-session.py': '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': 'd04608ad80a90288c32705bbfcfd3855738d7b09f207ae2aa4268f7c0a167037', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}, 'adapter_revision': 'usb-irq-native-pm-budget504-01'}, 'notes': {'samurai_usb_input': '08523f9f969b00a278a87ddd5d27ec3b54ac9b53a9c84f6429c4ecf5934c0f3f', 'samurai_gauge_protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai_mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}, 'system_pm_link': True}, 'restored_502': {'version': '#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026', 'image': '085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955', 'logdump': 'ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1', 'manifest_sha256': '18e8a1049a2c497fbc47ace50f8319aefccd63a9cd1ce5a7e9ef06916773b4e5', 'manifest': {'release': '7.3.0-rc6-rmx1931-samurai-k363+', 'modules': {'samurai-mp2650': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko', 'sha256': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd'}, 'samurai-usb-input': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko', 'sha256': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f'}, 'samurai-gauge-protection': {'target': '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko', 'sha256': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}}, 'default_input_cap_ua': 900000, 'default_charge_cap_ua': 250000, 'source_budget_enforced': True, 'installed_files': {'/usr/sbin/samurai-charging': '61451ffea87cca466dbbb2f1a2c6e7c05d0eee517479e8b019d43b1869355aa4', '/etc/init.d/samurai-charging': 'bfed48ebbcaced5f017110564045eef500a88f12fefe7ebff6d1e74cabfe570a', '/usr/lib/samurai-charging/control-trial.py': 'c33cb2eec24031e72a5f1dda9b94c05607615e0b12a14ba3cecd6db56c820761', '/usr/lib/samurai-charging/live-session.py': '2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-mp2650.ko': '97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-usb-input.ko': '7cbf10c0f74609effb415c30145e58b0fbe554511ef55a96baeeaf367c94ff5f', '/lib/modules/7.3.0-rc6-rmx1931-samurai-k363+/extra/samurai-charging/samurai-gauge-protection.ko': '7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044'}, 'adapter_revision': 'usb-irq-protection-observer-01'}, 'notes': {'samurai_usb_input': 'a845cd08aa415ca01ad4791b8c66047a927577e76439e632c73b6b4e2cff8c6d', 'samurai_gauge_protection': 'fc0d253d556b6ba656db263aaa50c37e3af2c7fe115b67e6b02641ae8b5733ec', 'samurai_mp2650': 'fe15a2fcb618dee0b161952cd66c32f2d5ecc9c8d50b0975242da5353c472016'}, 'system_pm_link': False}}
EXPECTED_VERSION=EXPECTED_LOGDUMP=EXPECTED_IMAGE=EXPECTED_REVISION=None


def need(ok, message):
    if not ok:
        raise RuntimeError(message)

def validate_cache(value):
 need(isinstance(value,dict) and set(value)=={'sha256','raw_base64','attribute_dev','attribute_inode','instance_inode'},'actual current cache fields')
 raw=base64.b64decode(value['raw_base64'],validate=True)
 need(0<len(raw)<16384 and raw.endswith(b'\n') and re.fullmatch('[0-9a-f]{64}',value['sha256']) and
  sha(raw)==value['sha256'],'exact current opaque cache bytes')
 first=dict(x.split('=',1) for x in raw.decode().splitlines()[0].split())
 need(first.get('schema')=='1' and (first.get('attempted'),first.get('terminal')) in [('0','0'),('1','1')],
  'fixed7848 cache must be untouched or already terminal; no capture in progress')
 need(type(value['attribute_dev']) is int and value['attribute_dev']>=0 and
  all(type(value[k]) is int and value[k]>0 for k in ['attribute_inode','instance_inode']),'current kernfs instance identity')
 return raw

INSTANCE='/sys/devices/platform/samurai-gauge-protection'

class CacheEvidence:
 def cache_evidence(self):
  need(self.mac_fd is not None,'held current cache fd')
  p=Path(INSTANCE);held,current=os.fstat(self.mac_fd),(p/'mac_evidence').stat()
  need((held.st_dev,held.st_ino)==(current.st_dev,current.st_ino) and
   (p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','same bound current cache fd')
  os.lseek(self.mac_fd,0,os.SEEK_SET);raw=os.read(self.mac_fd,16384)
  value=dict(sha256=sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=held.st_dev,
   attribute_inode=held.st_ino,instance_inode=p.stat().st_ino)
  validate_cache(value);need(self.baseline is None or value==self.baseline,'same current cache throughout read-only bracket')
  return value

class CacheFile:
    def __init__(self):
        self.mac_fd=None;self.baseline=None
    def open_cache(self):
        p=Path(INSTANCE)
        need((p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','current protection driver')
        self.mac_fd=os.open(p/'mac_evidence',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        self.baseline=self.cache_evidence()
    def close(self):
        if self.mac_fd is not None:
            try:os.close(self.mac_fd)
            finally:self.mac_fd=None

class CacheReader(CacheEvidence,CacheFile):
    pass

def links(device):
 result=[]
 for pattern in ['supplier:*','consumer:*']:
  for entry in sorted(device.glob(pattern)):
   item={'name':entry.name}
   try:
    target=entry.resolve(strict=True);item['target']=str(target)
    for name in ['consumer','supplier']:
     link=target/name
     if link.is_symlink():item[name]=str(link.resolve(strict=True))
    for name in ['runtime_pm','sync_state_only','status']:
     if (target/name).exists():item[name]=read(target/name)
   except OSError as error:item['errno']=error.errno
   result.append(item)
 return result

def pm_snapshot(device):
 return dict(path=str(device),of_node=str((device/'of_node').resolve()),
  compatible=read(device/'of_node/compatible'),usb_psy_name=read(device/'of_node/usb-psy-name'),
  power={name:read(device/'power'/name) for name in ['control','runtime_status','runtime_suspended_time','runtime_active_time','autosuspend_delay_ms']},links=links(device))


def configure_profile(request):
 global EXPECTED_VERSION,EXPECTED_LOGDUMP,EXPECTED_IMAGE,EXPECTED_REVISION,COHORT_MANIFEST,COHORT_EXPECTED_MANIFEST,COHORT_NOTES
 assert request['profile'] in PROFILES,'explicit postboot profile'
 row=PROFILES[request['profile']]
 EXPECTED_VERSION=row['version'];EXPECTED_LOGDUMP=row['logdump'];EXPECTED_IMAGE=row['image']
 COHORT_MANIFEST=row['manifest_sha256'];COHORT_EXPECTED_MANIFEST=row['manifest'];COHORT_NOTES=row['notes']
 EXPECTED_REVISION=row['manifest']['adapter_revision']
 return row

def validate_request(request):
 row=configure_profile(request);g=request['guard'];stage=request['stage'];a=request['activation_guard']
 assert request['schema']=='samurai-irq-native-usb-pm-postboot-readonly-v1'
 assert request['original_key_transport_verified'] is True and request['new_endpoint']=='fe80::62:bcff:fe28:a101%29'
 assert all(re.fullmatch('[0-9a-f]{64}',request[key]) for key in ['context_sha256','guard_sha256','stage_result_sha256'])
 assert re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',request['new_boot_id'])
 assert g['new_boot_id']==request['new_boot_id'] and g['boot_id']==a['boot_id']!=request['new_boot_id']
 assert g['target_kernel_version']==row['version'] and g['candidate_boot_sha256']==IRQ_BOOT and g['partitions']==['logdump']
 assert g['candidate_logdump_sha256']==row['logdump'] and g['image_sha256']==row['image']
 assert g['transaction_id']==stage['transaction_id'] and a['transaction_id']==request['activation_transaction_id']
 assert stage['terminal'] is stage['runtime_pending'] is stage['stop_verified'] is True and stage['primary_error'] is None
 assert not stage.get('receipt_error') and not stage.get('close_error')
 if request['profile']=='forward_504':
  assert re.fullmatch(r'irq-native-usb-pm-activate-[a-z0-9-]{8,48}',a['transaction_id'])
  assert re.fullmatch(r'irq-native-usb-pm-stage-[a-z0-9-]{8,48}',stage['transaction_id'])
  assert g['source_kernel_version']==a['source_kernel_version']==PROFILES['restored_502']['version']
  assert a['kernel_version']==row['version']
  assert stage['schema']=='samurai-irq-native-usb-pm-stage-result-v1' and stage['staged'] is True
  assert stage['status']=='staged/runtime_pending' and stage['disk_state']=='all_new_fsynced'
  assert stage['old_manifest_sha256']==PROFILES['restored_502']['manifest_sha256'] and stage['new_manifest_sha256']==row['manifest_sha256']
  assert not stage.get('recovery_error')
 else:
  assert re.fullmatch(r'irq-native-usb-pm-rollback-activate-[a-z0-9-]{8,48}',a['transaction_id'])
  assert re.fullmatch(r'irq-native-usb-pm-rollback-[a-z0-9-]{8,48}',stage['transaction_id'])
  assert g['source_kernel_version']==a['kernel_version'] and g['source_kernel_version'] in [p['version'] for p in PROFILES.values()]
  assert stage['schema']=='samurai-irq-native-usb-pm-cold-rollback-result-v1' and stage['restored'] is True
  assert stage['status']=='staged_original/runtime_pending' and stage['disk_state']=='all_original_fsynced'
  assert stage['unknown_write_state'] is False
 return row

def collect_pm_topology():
 controller=Path('/sys/bus/platform/devices/a600000.usb').resolve(strict=True)
 provider=Path('/sys/class/power_supply/samurai-usb-input/device').resolve(strict=True)
 return dict(controller=pm_snapshot(controller),provider=pm_snapshot(provider))

def check_pm_topology(raw,request):
 row=PROFILES[request['profile']];topology=raw['native_pm'];controller=topology['controller'];provider=topology['provider']
 assert controller['path'].startswith('/sys/devices/platform/') and controller['path'].endswith('/a600000.usb')
 assert controller['of_node']=='/sys/firmware/devicetree/base/soc@0/usb@a6f8800/usb@a600000'
 assert controller['compatible'].rstrip('\0')=='snps,dwc3' and controller['usb_psy_name'].rstrip('\0')=='samurai-usb-input'
 assert provider['path']==raw['irq_before']['device']==raw['irq_after']['device'] and provider['of_node']==NODE
 assert controller['power']['control']=='on' and controller['power']['runtime_status']=='active','current DEVICE/on/active premise'
 forward=[link for link in controller['links'] if link.get('supplier')==provider['path']]
 reverse=[link for link in provider['links'] if link.get('consumer')==controller['path']]
 if row['system_pm_link']:
  assert len(forward)==len(reverse)==1
  assert forward[0]['target']==reverse[0]['target'] and forward[0]['consumer']==controller['path'] and reverse[0]['supplier']==provider['path']
  for link in forward+reverse:
   assert link['runtime_pm']=='0' and link['sync_state_only']=='0' and link['status']=='not tracked','stateless-only native dependency'
 else:assert not forward and not reverse,'restored original native provider has no added PM link'
 return dict(native_DEVICE_on_active=True,stateless_dependency_observed=bool(forward),
  expected_dependency=row['system_pm_link'],system_suspend_or_resume_or_USB_recovery_accepted=False)

def check_cache(raw):
 before,after=raw['protection_cache_before'],raw['protection_cache_after']
 validate_cache(before);validate_cache(after);assert before==after,'same held protection instance/cache'
 return dict(same_readonly_cache_instance=True,new_capture_issued=False)

def collect(request,raw=None):
 validate_request(request)
 if raw is None:raw={}
 start=time.clock_gettime_ns(time.CLOCK_BOOTTIME);prior=identity();check_identity(prior,request['guard'])
 reader=CacheReader()
 try:
  reader.open_cache();raw['protection_cache_before']=reader.cache_evidence()
  collect_base(request,raw)
  raw['native_pm']=attempt(collect_pm_topology)
  raw['protection_cache_after']=reader.cache_evidence()
  raw['identity_after']=identity();raw['started_boottime_ns']=start
  raw['ended_boottime_ns']=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
  return raw
 finally:reader.close()

if __name__=='__main__':raise SystemExit(main(request=globals().get('POSTBOOT_REQUEST')))
