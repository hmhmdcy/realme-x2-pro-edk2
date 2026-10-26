"""Stage-aware device gates. Source only; no device action on definition."""
import base64,fcntl,hashlib,json,os,re,runpy,stat,struct,sys,time,uuid
from pathlib import Path

ROOT=Path('/root/charging-management-20261023')
SERVICE_LOCK='/run/lock/samurai-charging.lock'
STAGE_WORKER='47794e53b8f31e974a968cb6610c69a49e456042be940bca7104bb182595c83a'
STAGE_SUPERVISOR='b29ab985159ecc911571514cdc5fa72a1a44886037e35ff024dfa6fe623440cc'
LIVE_PATH='/usr/lib/samurai-charging/live-session.py'
LIVE_SHA='2199d7d413b2f4a5aeaa8270c20e967f5da711397c29e959e59463c1a5715f2b'
_SERVICE_FD=None


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


def stage_paths(transaction):
 need(re.fullmatch(r'usb-irq-protection-stage-[a-z0-9-]{8,48}',transaction),'stage name')
 root=ROOT/transaction;out=root/'device-stage'
 return {**{k:str(root/v) for k,v in {
  'request':'request-private.json','worker_launch':'worker-launch-receipt-private.json',
  'worker_terminal':'worker-terminal-private.json','supervisor_launch':'launch-receipt-private.json',
  'supervisor_process':'supervisor-process-private.json','supervisor_terminal':'supervisor-terminal-private.json',
  'worker_source':'stage-worker.py','supervisor_source':'stage-supervisor.py'}.items()},
  **{k:str(out/v) for k,v in {'result':'result.json','before':'before-private.json',
  'stopped':'stopped-private.json','after':'after-private.json','worker_process':'process-private.json',
  'adoption_proof':'adoption-proof-private.json'}.items()}}


def validate_stage_records(meta,records,processes,claim):
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
 need(stage['evidence']['request']['sha256']==stage['request_sha256'] and stage['evidence']['result']['sha256']==stage['result_sha256'],'request/result raw binding')
 need(stage['evidence']['worker_source']['sha256']==STAGE_WORKER and stage['evidence']['supervisor_source']['sha256']==STAGE_SUPERVISOR,'source evidence hashes')
 req=records['request'];result=records['result'];w=records['worker_process'];s=records['supervisor_process']
 need(set(req)=={'schema','transaction_id','cohort_delivery_sha256','payload_sha256','payload_base64',
  'worker_sha256','identity','adoption','lease_token'},'original request exact fields')
 need(req['schema']=='samurai-usb-irq-protection-stage-request-v1' and req['transaction_id']==tx and req['worker_sha256']==STAGE_WORKER,'original stage request')
 need(req['cohort_delivery_sha256']==FIXED['cohort_delivery_sha256'] and req['payload_sha256']==PAYLOAD,'original payload request')
 need(sha(base64.b64decode(req['payload_base64'],validate=True))==PAYLOAD and re.fullmatch('[0-9a-f]{48}',req['lease_token']),'actual original payload/lease identity')
 expected_identity=dict(boot_id=meta['boot_id'],version=FIXED['kernel_version'],serial_sha256=meta['soc_serial_sha256'],
  compatible_sha256=meta['compatible_sha256'],rootfs_sha256=meta['rootfs_release_sha256'])
 need(req['identity']==expected_identity,'same actual source identity')
 need(req['adoption']=={k:meta['adoption'][k] for k in ['transaction_id','guard_path','guard_sha256','postboot_raw_sha256']},'same actual adoption')
 need(result['schema']=='samurai-usb-irq-protection-stage-result-v1' and result['transaction_id']==tx and
  result['cohort_delivery_sha256']==FIXED['cohort_delivery_sha256'] and result['payload_sha256']==PAYLOAD,'stage result binding')
 need(result['terminal'] is True and result['staged'] is True and result['phase']=='staged' and
  result['status']=='staged/runtime_pending' and result['runtime_pending'] is True and
  result['disk_state']=='all_new_fsynced' and result['stop_verified'] is True and result['unknown_write_state'] is False,'successful complete stage terminal')
 need(all(result.get(k) is None for k in ['primary_error','stop_error','receipt_error','close_error']),'no stage outcome/receipt/close error')
 need(all(result.get(k) is False for k in ['activation_attempted','new_module_loaded','capture_issued','automatic_rollback_or_replay']),'stage did not activate/replay')
 need(result['source_boot_id']==meta['boot_id'] and result['source_version']==FIXED['kernel_version'] and
  result['source_guard_path']==meta['adoption']['guard_path'],'stage source not a prior boot')
 need(result['old_manifest_sha256']==FIXED['source_manifest_sha256'] and result['new_manifest_sha256']==FIXED['charging_manifest_sha256'],'stage old/new manifests')
 need(result['old_resident_notes']==OLD_NOTES and result['resident_notes_expected']==OLD_NOTES,'retained old resident notes')
 need(set(result['final_files'])==set(FIXED['new_disk_files']) and set(result['temporary_files'])==set(FIXED['new_disk_files']),'exact staged three-file set')
 for name,digest in FIXED['new_disk_files'].items():
  item=result['final_files'][name]
  need(item['sha256']==digest and item['new_sha256']==digest and item['old_sha256']==OLD_FILES[name] and item['mode']=='0o600' and item['classification']=='new','staged final readback')
  need(result['temporary_files'][name]['state']=='absent','no unknown/retained atomic temporary')
 wargv=['python3','-B',str(ROOT/tx/'stage-worker.py'),'--execute-stage']
 sargv=['python3','-B',str(ROOT/tx/'stage-supervisor.py'),'--execute-supervisor']
 for receipt,argv in [(w,wargv),(s,sargv)]:
  need(type(receipt['pid']) is int and receipt['pid']>0 and type(receipt['start_ticks']) is int and receipt['start_ticks']>0 and
   receipt['transaction_id']==tx and receipt['boot_id']==meta['boot_id'] and receipt['argv']==argv,'original process self receipt')
 need(w['worker_sha256']==STAGE_WORKER and s['request_sha256']==stage['request_sha256'],'original worker/supervisor source request')
 wl=records['worker_launch'];wt=records['worker_terminal'];sl=records['supervisor_launch'];st=records['supervisor_terminal']
 for item,pid,argv in [(wl,w['pid'],wargv),(wt,w['pid'],wargv),(sl,s['pid'],sargv),(st,s['pid'],sargv)]:
  need(item['pid']==pid and item['argv']==argv and item['transaction_id']==tx and item['boot_id']==meta['boot_id'] and
   item['request_sha256']==stage['request_sha256'],'same original child request')
 need(wl['supervisor_pid']==wt['supervisor_pid']==s['pid'] and wl.get('start_ticks') in [None,w['start_ticks']],'worker supervised instance')
 need(sl.get('start_ticks') in [None,s['start_ticks']] and st['start_ticks']==s['start_ticks'],'supervisor original instance')
 need(wt['terminal'] is True and type(wt['returncode']) is int and wt['returncode']==0 and
  st['terminal'] is True and type(st['returncode']) is int and st['returncode']==0 and
  st['worker_pid']==w['pid'] and type(st['worker_returncode']) is int and st['worker_returncode']==0,'both original Popen terminals')
 need(claim['transaction_id']==tx and claim['boot_id']==meta['boot_id'] and claim['request_sha256']==stage['request_sha256'] and
  claim['request_count']==1 and claim['argv']==wargv and claim['supervisor_argv']==sargv and
  claim['supervisor_sha256']==STAGE_SUPERVISOR,'original launch claim')
 for key,receipt in [('worker',w),('supervisor',s)]:
  observed=processes[key]
  need(observed['pid']==receipt['pid'] and observed['state'] in ['absent','zombie'],'original mutator not alive/unknown/reused')
  if observed['state']=='zombie':need(observed['start_ticks']==receipt['start_ticks'],'same zombie instance')
 need(records['adoption_proof']['actual_fresh_validation_sha256']==result['adoption_fresh_validation_sha256']==meta['adoption']['fresh_validation_sha256'],'original adoption proof hash')
 return req


def read_stage(meta):
 stage=meta['stage'];root=owned_directory(ROOT/stage['transaction_id']);owned_directory(root/'device-stage')
 records={}
 for key,path in stage_paths(stage['transaction_id']).items():
  item=stage['evidence'][key];need(item['path']==path,'original stage path')
  raw=raw_owned(path);need(sha(raw)==item['sha256'],'stage original bytes changed: '+key)
  if key not in ['worker_source','supervisor_source']:records[key]=json.loads(raw)
 processes={k:process_observation(records[k+'_process']) for k in ['worker','supervisor']}
 claim=json.loads(raw_owned(root/'launch-claim-private.json'))
 request=validate_stage_records(meta,records,processes,claim)
 proof=raw_owned(Path(meta['adoption']['guard_path']).parent/'fresh-validation-private.json')
 need(sha(proof)==meta['adoption']['fresh_validation_sha256'],'actual original adoption validation')
 validate_adoption(json.loads(proof),request)
 return records


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


def validate_meta_shape(meta,guard_path):
 need(guard_path.is_absolute() and guard_path.name=='guard-private.json','private guard path')
 need(set(meta)==set(FIXED)|{'transaction_id','token','boot_id','soc_serial_sha256','compatible_sha256',
  'rootfs_release_sha256','adoption','stage'},'exact activation fields')
 need(all(meta.get(k)==v for k,v in FIXED.items()),'new fixed activation profile')
 need(re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}',meta['transaction_id']) and
  re.fullmatch('[0-9a-f]{32,64}',meta['token']),'new independent activation')
 need(guard_path.parent==ROOT/meta['transaction_id'],'new activation directory')


def validate_activation_guard(guard_path,allow_inhibit=False):
 need(os.geteuid()==0 and not sys.flags.optimize,'root non-optimized worker')
 guard_path=secure_file(guard_path);meta=json.loads(raw_owned(guard_path))
 validate_meta_shape(meta,guard_path)
 owned_directory(guard_path.parent);acquire_service_lock()
 need(str(uuid.UUID(meta['boot_id']))==meta['boot_id'] and meta['boot_id']==Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'actual original #502 boot')
 need(os.uname().machine=='aarch64' and os.uname().release==FIXED['kernel_release'] and os.uname().version==FIXED['kernel_version'],'exact adopted Image502')
 need(Path('/proc/sys/kernel/tainted').read_text().strip()=='0','taint')
 need(file_sha('/etc/samurai-rootfs-release')==meta['rootfs_release_sha256'],'rootfs')
 serial=Path('/sys/devices/soc0/serial_number').read_bytes();compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
 need(serial.strip() and sha(serial)==meta['soc_serial_sha256'] and sha(compatible)==meta['compatible_sha256'] and b'realme,samurai' in compatible.split(b'\0'),'board identity')
 adoption=meta['adoption'];need(set(adoption)=={'transaction_id','guard_path','guard_sha256','postboot_raw_sha256','fresh_validation_sha256'},'adoption fields')
 need(re.fullmatch(r'image502-[a-z0-9-]{8,64}',adoption['transaction_id']) and
  adoption['guard_path']=='/var/lib/samurai/'+adoption['transaction_id']+'-adopted/boot-id-private.txt','actual 502 adoption path')
 for key in ['guard_sha256','postboot_raw_sha256','fresh_validation_sha256']:need(re.fullmatch('[0-9a-f]{64}',adoption[key]),'adoption raw digest')
 owned_directory(Path(adoption['guard_path']).parent)
 guard=raw_owned(adoption['guard_path']);need(guard==(meta['boot_id']+'\n').encode() and sha(guard)==adoption['guard_sha256'],'actual adopted guard bytes')
 records=read_stage(meta)
 need(block_sha('/dev/disk/by-partlabel/boot',100663296)==FIXED['rollback_boot_sha256'] and
  block_sha('/dev/disk/by-partlabel/logdump',67108864)==FIXED['unchanged_logdump_sha256'],'current complete carriers read-only')
 need(file_sha('/usr/share/samurai-charging/manifest.json')==FIXED['charging_manifest_sha256'],'new staged disk manifest')
 manifest=json.loads(Path('/usr/share/samurai-charging/manifest.json').read_bytes())
 need(manifest==EXPECTED_MANIFEST,'exact new manifest structure')
 for path,digest in manifest['installed_files'].items():need(file_sha(path)==digest,'current retained/new file: '+path)
 for path,digest in FIXED['new_disk_files'].items():need(sha(raw_owned(path))==digest,'three actual new disk files')
 for name,digest in FIXED['old_resident_notes'].items():
  need(sha(Path('/sys/module',name,'notes/.note.gnu.build-id').read_bytes())==digest and Path('/sys/module',name,'initstate').read_text().strip()=='live','old live note independent of new disk')
 need(Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y' and not Path('/sys/module/samurai_usbin_init').exists(),'native provider retained/no helper')
 need(file_sha(FIXED['startup500_path'])==FIXED['startup500_sha256'] and Path('/sys/kernel/config/usb_gadget/samurai/configs/c.1/MaxPower').read_text().strip()=='500','startup/descriptor500')
 need(Path('/sys/module/bq27xxx_battery/parameters/samurai_instant_current').read_text().strip()=='Y' and
  [x for x in Path('/proc/cmdline').read_text().split() if x.startswith('bq27xxx_battery.samurai_instant_current=')]==['bq27xxx_battery.samurai_instant_current=1'],'current gauge opt-in')
 eud_off_check();camera481_check(guard_path.parent/'camera481-expected-private.json')
 data=observe_staged();staged_health(data,time.clock_gettime(time.CLOCK_BOOTTIME))
 if not allow_inhibit:environment(data)
 phase=Path('/run')/(meta['transaction_id']+'-reboot-phase-private.json');need(not phase.exists(),'restart already claimed; inspect original only')
 return meta,Path('/var/lib/samurai')/meta['transaction_id'],phase
