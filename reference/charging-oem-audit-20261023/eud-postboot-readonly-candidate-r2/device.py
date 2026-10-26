"""One-shot postboot reads only. Default --check-local never collects.
No SSH implementation, guard adoption, CSR access or automatic recovery.
"""
from pathlib import Path
import argparse,base64,fcntl,hashlib,json,mmap,os,re,stat,struct,subprocess,sys,time
sha=lambda raw:hashlib.sha256(raw).hexdigest()
CANDIDATE_BOOT='4126a2978bc79b5cb95b6e1b86bb432a6b16ece627776237c163b93b323bbfcf'
ROLLBACK_BOOT='a30fb4440726e1c3ab80ad65277db4e57fec9a0924380cc07830a5c6e69ec280'
IMAGE363='15746aab311eed32478cdee4e13c1677716ff48c8a04316c9c15cf606c9d6468'
LOGDUMP365='aca01bc2c91928f1a6a6690f62d14db014351ec5049e5684590b40c3c93de8da'
CAMERA481='1c4584915dade64a0978a0138c6775bf99e56af9f8036d7d2276c33f132f4705'
R8_MANIFEST='320316c3d93c1dbcaae29440f1f17d72c75e4994d656a9da9fcd5aeb93c10a1f'
R8_NOTES={'samurai_usb_input':'f0edb792d30ee1168ee1793e89707aa48b2085c845acde8f472f2c13a03804b0',
 'samurai_gauge_protection':'930e0e1f34e89e4e06a7632ca14a26181975f9f35e55a51209af71480b56fe76',
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


def read_ring():
 import base64,mmap,struct,sys
 start,total=0x9ffe3000,0x14000
 assert os.sysconf('SC_PAGE_SIZE')==4096
 cover=[]
 for line in Path('/proc/iomem').read_text().splitlines():
  match=re.fullmatch(r'\s*([0-9a-f]+)-([0-9a-f]+) : (.*)',line)
  if match and int(match[1],16)<=start and int(match[2],16)>=start+total-1:
   cover.append((line,match[3]))
 assert cover and cover[-1][1]=='reserved', 'RAM range not covered by a reserved leaf'
 fd=os.open('/dev/mem',os.O_RDONLY|os.O_SYNC|os.O_CLOEXEC)
 try:
  with mmap.mmap(fd,total,flags=mmap.MAP_SHARED,prot=mmap.PROT_READ,offset=start) as view:
   before=bytes(view[:32])
   fields=struct.unpack('<8I',before)
   print(json.dumps({'phase':'header','fields':fields}),file=sys.stderr,flush=True)
   assert fields[:3]==(0x474f4c45,0x10000,total-32), 'Unexpected ring header; no data read'
   assert ((fields[3]-fields[4])&0xffffffff)<=total-32, 'Invalid head/tail distance'
   raw=bytes(view[:total])
   after=bytes(view[:32])
 finally:
  os.close(fd)
 return {'raw_b64':base64.b64encode(raw).decode(), 'header_before':list(fields),
         'header_after':list(struct.unpack('<8I',after)), 'header_stable':before==raw[:32]==after,
         'reserved_cover':[x[0] for x in cover], 'physical_start':start, 'mapped_bytes':total,
         'explicit_memory_bytes_read':total+64, 'hardware_writes':0}

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
 assert r['uname']['machine']=='aarch64' and r['taint']=='0'
 assert r['uname']['release']==g['kernel_release']=='7.3.0-rc6-rmx1931-samurai-k363+'
 assert r['uname']['version']==g['kernel_version'] and r['uname']['version'].startswith('#363 ')
 check_file(r['rootfs'],g['rootfs_release_sha256'])
 assert r['serial_sha256']==g['soc_serial_sha256']
 compatible=base64.b64decode(r['compatible_b64'],validate=True)
 assert sha(compatible)==g['compatible_sha256'] and b'realme,samurai' in compatible.split(b'\0')
 return {'new_boot':True,'same_board_kernel_rootfs':True}

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

def collect(request,raw=None):
 if raw is None:raw={}
 raw.update(identity_before=identity(),started_boottime_ns=time.clock_gettime_ns(time.CLOCK_BOOTTIME))
 # No partition or RAM mapping before actual new-boot/board/kernel/rootfs match.
 initial=attempt(lambda:check_identity(raw['identity_before'],request['guard']))
 raw['identity_gate']=initial
 if 'error' in initial:return raw
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
 # The only /dev/mem mapping is the existing reserved RAM ring; never CSR.
 if raw['boot_partition'].get('sha256')==CANDIDATE_BOOT and raw['logdump_partition'].get('sha256')==LOGDUMP365:
  raw['ring']=attempt(read_ring)
 else:raw['ring']={'not_read':'partition identity gate failed'}
 raw['dmesg']=command(['dmesg'])
 raw['identity_after']=identity();raw['ended_boottime_ns']=time.clock_gettime_ns(time.CLOCK_BOOTTIME)
 return raw

def check_partitions(r):
 assert r['boot_partition']['bytes']==100663296 and r['boot_partition']['sha256']==CANDIDATE_BOOT
 assert r['logdump_partition']['bytes']==67108864 and r['logdump_partition']['sha256']==LOGDUMP365
 return {'candidate_boot_exact':True,'logdump_exact':True,'Image363_binding':'existing FAT mcopy/complete-logdump receipt'}

def check_install(r):
 check_file(r['manifest'],R8_MANIFEST);m=json.loads(r['manifest_text'])
 assert m['adapter_revision']=='r8' and m['release']==r['identity_before']['uname']['release']
 assert set(m['modules'])=={n.replace('_','-') for n in R8_NOTES}
 for p,digest in m['installed_files'].items():check_file(r['installed_files'][p],digest)
 for n,info in m['modules'].items():
  f=r['charging_modules'][n];check_file(f,info['sha256'])
  assert f['loaded_note_matches_disk'] and f['loaded_note_sha256']==R8_NOTES[n.replace('-','_')]
  assert f['intree']['exit']==0 and f['intree']['stdout'].strip()=='Y'
  assert r['charging_module_live'][n]=='live'
 assert r['retained']=='Y' and r['helper_absent']
 return {'R8_disk_and_live_notes':True}

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
 assert int(r['config_max_power_ma'])==100
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

def decode_ring(ring):
 assert 'raw_b64' in ring,'no valid reserved ring capture'
 raw=base64.b64decode(ring['raw_b64'],validate=True);assert len(raw)==0x14000
 fields=struct.unpack('<8I',raw[:32])
 assert ring['header_stable'] and list(fields)==ring['header_before']==ring['header_after']
 assert fields[:3]==(0x474f4c45,0x10000,len(raw)-32) and ((fields[3]-fields[4])&0xffffffff)<=fields[2]
 head,size=fields[3],fields[2];count=min(head,size);oldest=head-count;data=raw[32:]
 history=bytes(data[(oldest+i)%size] for i in range(count))
 receipts=[line.decode('ascii') for line in history.splitlines() if re.fullmatch(rb'\[SAMURAI-EUD-OFF\] attempted=[01] write=[01] arm=[0-9a-fA-F]{8} before=[0-9a-fA-F]{8} after=[0-9a-fA-F]{8} status=[A-Za-z0-9 _-]{1,64}',line)]
 parsed=[]
 for line in receipts:
  x=re.fullmatch(r'\[SAMURAI-EUD-OFF\] attempted=([01]) write=([01]) arm=([0-9a-fA-F]{8}) before=([0-9a-fA-F]{8}) after=([0-9a-fA-F]{8}) status=([A-Za-z0-9 _-]{1,64})',line)
  parsed.append(dict(attempted=int(x[1]),write=int(x[2]),arm=int(x[3],16),before=int(x[4],16),after=int(x[5],16),status=x[6]))
 # A bounded retained history is not a proof of Head never wrapping or marker age.
 valid=len(parsed)==1 and parsed[0]['attempted']==1 and parsed[0]['arm'] in [0,1,0x01010101] and parsed[0]['before'] in [0,1,0x01010101] and parsed[0]['after']==0 and parsed[0]['status']=='Success' and parsed[0]['write']==int(parsed[0]['before']!=0)
 return {'ready':valid,'marker_state':'one_well_formed_off_report' if valid else 'missing_ambiguous_or_failure_receipt',
   'receipts':receipts,'parsed':parsed,'raw_sha256':sha(raw),'header':list(fields),
   'history_assumption':'No 32-bit Head wrap proven; count=min(Head,Size) is bounded decode only.',
   'receipt_absence_is_not_callback_failure':True,'callback_success_independently_proven':False,
   'physical_route_or_SDP500_accepted':False}

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

def audit(r,request):
 result={'passed':False,'checks':{},'errors':{},'read_only':True,'guard_created':False,'hardware_writes':0,
         'physical_route_or_icon_or_SDP500_accepted':False}
 checks=[('identity',lambda:check_identity(r['identity_before'],request['guard'])),
  ('partitions',lambda:check_partitions(r)),('R8_install',lambda:check_install(r)),
  ('charging',lambda:check_charging(r)),('camera481',lambda:check_camera(r,request['camera']['expected'])),
  ('EUD_producers',lambda:check_producers(r)),('EUD_ring_receipt',lambda:decode_ring(r['ring'])),
  ('services_faults',lambda:check_services(r)),
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
 p.add_argument('--window-confirmed',action='store_true');p.add_argument('--new-endpoint')
 args=p.parse_args(argv)
 if not args.execute:
  print(json.dumps({'local_checks_passed':True,'device_accessed':False,'read_only':True}));return 0
 assert args.window_confirmed and args.new_endpoint and request is not None
 assert request['schema']=='samurai-eud-postboot-readonly-v1'
 assert request['original_key_transport_verified'] is True and request['new_endpoint']==args.new_endpoint
 assert request['guard']['candidate_boot_sha256']==CANDIDATE_BOOT
 raw={}
 try:
  collect(request,raw);result=audit(raw,request)
 except Exception as e:result={'passed':False,'read_only':True,'collection_error':type(e).__name__,'message':str(e)}
 print(json.dumps({'schema':request['schema'],'transaction_id':request['guard']['transaction_id'],
   'context_sha256':request['context_sha256'],'guard_sha256':request['guard_sha256'],
   'raw':raw,'result':result}),flush=True)
 return 0 if result['passed'] else 1

if __name__=='__main__':raise SystemExit(main(request=globals().get('POSTBOOT_REQUEST')))
