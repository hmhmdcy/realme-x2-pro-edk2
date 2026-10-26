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
