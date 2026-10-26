PROFILES=('staged_same_boot_old_resident','booted_504_new_resident','booted_502_new_resident')

def expected_profile(request):
 index=PROFILES.index(request['profile'])
 return {'version':VERSION504 if index==1 else VERSION502,'boot':BOOT,
  'logdump':LOGDUMP504 if index==1 else LOGDUMP502,'notes':OLD_NOTES if index==0 else NEW_NOTES}

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

def unpack(request):
 need(set(request)=={'schema','transaction_id','profile','identity','source_identity','source_stage','source_stage_observations',
  'activation','current_cache','payload_sha256','payload_base64','worker_sha256','lease_token'},'current rollback request fields')
 need(request['schema']=='samurai-irq-native-usb-pm-cold-rollback-request-v1' and
  re.fullmatch(r'irq-native-usb-pm-rollback-[a-z0-9-]{8,48}',request['transaction_id']),'new cold rollback transaction')
 need(request['profile'] in PROFILES,'explicit current profile')
 for identity in [request['identity'],request['source_identity']]:
  need(set(identity)=={'boot_id','version','serial_sha256','compatible_sha256','rootfs_sha256'} and
   str(uuid.UUID(identity['boot_id']))==identity['boot_id'],'complete actual identity')
  for key in ['serial_sha256','compatible_sha256','rootfs_sha256']:need(re.fullmatch('[0-9a-f]{64}',identity[key]),'actual board identity digest')
 need(request['source_identity']['version']==VERSION502 and request['identity']['version']==expected_profile(request)['version'],
  'source502 and actual current profile version')
 need(re.fullmatch('[0-9a-f]{48}',request['lease_token']) and re.fullmatch('[0-9a-f]{64}',request['worker_sha256']),'actual worker/lease')
 validate_cache(request['current_cache'])
 raw=base64.b64decode(request['payload_base64'],validate=True)
 need(request['payload_sha256']==ROLLBACK_PAYLOAD and len(raw)==25858 and sha(raw)==ROLLBACK_PAYLOAD,'actual fixed two-file inverse')
 files={}
 with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
  members=tar.getmembers();need(len(members)==2,'exact original two files')
  for member in members:
   target='/'+member.name
   need(target in OLD_FILES and target not in files and member.name==target.lstrip('/') and member.isfile() and
    member.mode==0o600 and member.uid==member.gid==member.mtime==0 and member.uname==member.gname=='root' and
    not member.pax_headers,'exact old member metadata')
   data=tar.extractfile(member).read();need(sha(data)==OLD_FILES[target],'actual old member bytes');files[target]=data
 return files

def validate_profile(request,actual):
 current,source=request['identity'],request['source_identity'];profile=expected_profile(request)
 need(actual['identity']==current and all(current[k]==source[k] for k in ['serial_sha256','compatible_sha256','rootfs_sha256']),
  'same actual board/rootfs and exact current identity')
 need(current['version']==profile['version'] and source['version']==VERSION502 and actual['release']==RELEASE and
  actual['machine']=='aarch64' and actual['taint']=='0','actual complete kernel profile')
 need(actual['boot']==dict(bytes=100663296,sha256=profile['boot']) and actual['logdump']==dict(bytes=67108864,sha256=profile['logdump']),
  'complete current bootedd/FAT profile')
 need(actual['notes']==profile['notes'] and set(actual['module_states'])==set(profile['notes']) and
  all(v=='live' for v in actual['module_states'].values()),'actual resident module tuple')
 need(actual['current_cache']==request['current_cache'],'same current held cache instance')
 if request['profile']==PROFILES[0]:
  need(current==source and request['activation'] is None,'same-stage boot/old resident only')
 else:
  need(current['boot_id']!=source['boot_id'],'source boot ended; do not attribute its PIDs now')
  saved=request['activation']
  keys={'schema','activation_transaction_id','context_sha256','guard_sha256','flash_request_sha256','flash_result_sha256',
   'reboot_request_sha256','reboot_result_sha256','flash_claimed_ns','reboot_claimed_ns','boot_sha256','logdump_sha256','action_pair'}
  need(isinstance(saved,dict) and set(saved)==keys and saved['schema']=='samurai-irq-native-usb-pm-saved-activation-v1' and
   re.fullmatch(r'irq-native-usb-pm-activate-[a-z0-9-]{8,48}',saved['activation_transaction_id']),'actual saved original activation binding')
  for key in keys-{'schema','activation_transaction_id','flash_claimed_ns','reboot_claimed_ns','action_pair'}:
   need(re.fullmatch('[0-9a-f]{64}',saved[key]),'saved actual action digest')
  need(saved['boot_sha256']==BOOT and saved['logdump_sha256']==profile['logdump'] and
   type(saved['flash_claimed_ns']) is type(saved['reboot_claimed_ns']) is int and
   0<saved['flash_claimed_ns']<saved['reboot_claimed_ns'],'actual selected carrier and write/reboot order')
  pair=['flash-candidate','reboot-candidate'] if request['profile']==PROFILES[1] else ['rollback-original','reboot-original']
  need(saved['action_pair']==pair,'actual selected action pair')
 return {'profile':request['profile'],'resident_notes':profile['notes'],'boot_sha256':BOOT,
  'logdump_sha256':profile['logdump'],'current_version':profile['version']}

def stage_namespace():
 need(sha(STAGE_RULES.encode())==STAGE_RULES_SHA,'original current stage receipt rules')
 namespace={};exec(compile(STAGE_RULES,'frozen-current-stage-rules','exec'),namespace);return namespace

def source_paths(transaction):
 return stage_namespace()['stage_paths'](transaction)

def verify_source_records(request,raws,processes,claim):
 ns=stage_namespace();projection=request['source_stage'];paths=ns['stage_paths'](projection['transaction_id'])
 need(set(projection['evidence'])==set(paths) and set(raws)==set(paths),'complete actual seventeen source records')
 records={}
 for name,path in paths.items():
  item=projection['evidence'][name]
  need(set(item)=={'path','sha256'} and item['path']==path and item['sha256']==sha(raws[name]),'source original path/bytes: '+name)
  if name not in ['worker_source','supervisor_source']:
   records[name]=raws[name] if name in ['old_usb','old_manifest'] else json.loads(raws[name])
 original=records['request'];need(original['identity']==request['source_identity'],'actual original source identity')
 meta=dict(stage=projection,boot_id=original['identity']['boot_id'],soc_serial_sha256=original['identity']['serial_sha256'],
  compatible_sha256=original['identity']['compatible_sha256'],rootfs_release_sha256=original['identity']['rootfs_sha256'],adoption=original['adoption'])
 # Recheck the authenticated source-frame observations from its actual saved
 # same-boot fetch. These are historical, not new observations of old PIDs.
 captured=request['source_stage_observations'];need(set(captured)=={'worker','supervisor'},'original source-frame processes')
 ns['validate_stage_records'](meta,records,captured,claim)
 if request['identity']['boot_id']==request['source_identity']['boot_id']:
  ns['validate_stage_records'](meta,records,processes,claim)
 else:
  expected=dict(state='source_boot_ended',source_boot_id=request['source_identity']['boot_id'],current_boot_id=request['identity']['boot_id'])
  need(processes=={'worker':expected,'supervisor':expected},'never attribute current PIDs across source boot end')
 need(sha(raws['worker_source'])==STAGE_WORKER and sha(raws['supervisor_source'])==STAGE_SUPERVISOR,'fixed original stage sources')
 return {'source_stage_terminal_verified':True,'source_boot_id':request['source_identity']['boot_id'],
  'source_result_sha256':sha(raws['result']),'source_boot_ended':request['identity']['boot_id']!=request['source_identity']['boot_id'],
  'historical_process_observations_replayed':True,'host_transport_reaudited_here':False}

def retained(before,after):
 legacy_retained(before,after)
 need(before['current_cache']==after['current_cache'],'current protection instance/cache retained')
 b,a=before['sample'],after['sample']
 if b.get('logical_full')==1 and b.get('online')==a.get('online')==1:
  need(a.get('logical_full')==1 and a.get('full_cause')==b.get('full_cause') and a.get('session_seconds')==0,
   'online logical Full/cause retained while stopped')

class Device(BaseDevice):
 def __init__(self):
  super().__init__();self.mac_fd=None
 def identity(self):
  need(self.request is not None,'explicit current request')
  need(os.uname().version==expected_profile(self.request)['version'] and os.uname().release==RELEASE and
   os.uname().machine=='aarch64','exact current profile kernel')
  compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
  need(b'realme,samurai' in compatible.split(b'\0'),'actual board')
  return dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),version=os.uname().version,
   serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()),compatible_sha256=sha(compatible),
   rootfs_sha256=sha(read_owned('/etc/samurai-rootfs-release')[0]))
 def begin(self,request):
  super().begin(request)
  p=Path(INSTANCE);need((p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','current protection driver')
  self.mac_fd=os.open(p/'mac_evidence',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
  need(self.cache_evidence()==request['current_cache'],'fresh current cache matches original-key capture')
 def cache_evidence(self):
  need(self.mac_fd is not None,'held current cache fd')
  p=Path(INSTANCE);held,current=os.fstat(self.mac_fd),(p/'mac_evidence').stat()
  need((held.st_dev,held.st_ino)==(current.st_dev,current.st_ino) and
   (p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','same bound current cache fd')
  os.lseek(self.mac_fd,0,os.SEEK_SET);raw=os.read(self.mac_fd,16384)
  value=dict(sha256=sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=held.st_dev,
   attribute_inode=held.st_ino,instance_inode=p.stat().st_ino)
  validate_cache(value);need(value==self.request['current_cache'],'current cache/instance continuously retained')
  return value
 def source_proof(self,request):
  paths=source_paths(request['source_stage']['transaction_id']);raws={name:read_owned(path)[0] for name,path in paths.items()}
  original=json.loads(raws['request']);guard,mode=read_owned(original['adoption']['guard_path'])
  need(mode==0o600 and guard==(request['source_identity']['boot_id']+'\n').encode() and
   sha(guard)==original['adoption']['guard_sha256'],'retained actual original IRQ guard')
  different=request['identity']['boot_id']!=request['source_identity']['boot_id'];processes={}
  ns=stage_namespace()
  for role in ['worker','supervisor']:
   processes[role]=dict(state='source_boot_ended',source_boot_id=request['source_identity']['boot_id'],current_boot_id=request['identity']['boot_id']) if different else ns['process_observation'](json.loads(raws[role+'_process']))
  claim=json.loads(read_owned(Path(ROOT)/original['transaction_id']/'launch-claim-private.json')[0])
  result=verify_source_records(request,raws,processes,claim);self.log('source-stage-proof-private.json',result);return result
 def current(self,request,carriers=True):
  value=super().current(request,carriers);value['current_cache']=self.cache_evidence();return value
 def observe(self,manager):
  value=super().observe(manager);value['current_cache']=self.cache_evidence();return value
 def close(self):
  errors=[]
  if self.mac_fd is not None:
   try:os.close(self.mac_fd)
   except BaseException as error:errors.append(detail(error))
   finally:self.mac_fd=None
  try:super().close()
  except BaseException as error:errors.append(detail(error))
  need(not errors,'all owned cache/journal/lock close errors: '+repr(errors))
