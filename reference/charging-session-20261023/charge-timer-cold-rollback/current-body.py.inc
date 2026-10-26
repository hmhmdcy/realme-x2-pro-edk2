PROFILES=('staged_same_boot_old_charger','booted_504_new_charger')

def expected_profile(request):
    return dict(version=VERSION504,boot=BOOT,logdump=LOGDUMP504,
                notes=OLD_NOTES if request['profile']==PROFILES[0] else NEW_NOTES)

def validate_cache(value):
    need(isinstance(value,dict) and set(value)=={'sha256','raw_base64','attribute_dev','attribute_inode','instance_inode'},'complete current cache evidence')
    raw=base64.b64decode(value['raw_base64'],validate=True)
    need(0<len(raw)<16384 and raw.endswith(b'\n') and sha(raw)==value['sha256'],'complete same opaque cache bytes')
    header=dict(item.split('=',1) for item in raw.decode().splitlines()[0].split())
    need(header.get('schema')=='2' and header.get('diagnostic_profile')=='1' and
         (header.get('attempted'),header.get('terminal')) in [('0','0'),('1','1')],'f6 profile1 untouched or completed cache, never in progress')
    need(type(value['attribute_dev']) is int and value['attribute_dev']>=0 and
         all(type(value[k]) is int and value[k]>0 for k in ['attribute_inode','instance_inode']),'actual current kernfs identities')
    return raw

def unpack(request):
    need(set(request)=={'schema','transaction_id','profile','identity','source_identity','source_stage','current_cache',
         'payload_sha256','payload_base64','worker_sha256','lease_token'},'timer rollback request keys')
    need(request['schema']=='samurai-charger-timer-cold-rollback-request-v1' and
         re.fullmatch(r'charger-timer-cold-rollback-[a-z0-9-]{8,48}',request['transaction_id']),'explicit new timer rollback owner')
    need(request['profile'] in PROFILES and request['source_identity']==SOURCE_IDENTITY,'exact source identity and current profile')
    current=request['identity']
    need(set(current)==set(SOURCE_IDENTITY) and str(uuid.UUID(current['boot_id']))==current['boot_id'] and
         current['version']==VERSION504,'fresh current504 identity')
    need(all(current[k]==SOURCE_IDENTITY[k] for k in ['serial_sha256','compatible_sha256','rootfs_sha256']),'same actual board/rootfs')
    need(re.fullmatch('[0-9a-f]{48}',request['lease_token']) and re.fullmatch('[0-9a-f]{64}',request['worker_sha256']),'actual worker and unique lease')
    validate_cache(request['current_cache'])
    raw=base64.b64decode(request['payload_base64'],validate=True)
    need(request['payload_sha256']==ROLLBACK_PAYLOAD and len(raw)==51591 and sha(raw)==ROLLBACK_PAYLOAD,'exact c725 two-file inverse')
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        members=archive.getmembers();need(len(members)==2,'only charger and manifest')
        for member in members:
            target='/'+member.name
            need(target in OLD_FILES and target not in files and member.name==target.lstrip('/') and member.isfile() and
                 member.mode==0o600 and member.uid==member.gid==member.mtime==0 and member.uname==member.gname=='root' and
                 not member.pax_headers,'exact inverse member metadata')
            data=archive.extractfile(member).read();need(sha(data)==OLD_FILES[target],'original bytes');files[target]=data
    return files

def validate_profile(request,actual):
    profile=expected_profile(request);current=request['identity']
    need(actual['identity']==current and current['version']==VERSION504 and actual['release']==RELEASE and
         actual['machine']=='aarch64' and actual['taint']=='0','actual complete504 profile')
    need(actual['boot']==dict(bytes=100663296,sha256=BOOT) and actual['logdump']==dict(bytes=67108864,sha256=LOGDUMP504),'unchanged complete carriers')
    need(actual['notes']==profile['notes'] and set(actual['module_states'])==set(profile['notes']) and
         all(value=='live' for value in actual['module_states'].values()),'exact live charger/USB/protection tuple')
    need(actual['current_cache']==request['current_cache'],'same held current cache')
    if request['profile']==PROFILES[0]:need(current==SOURCE_IDENTITY,'original source boot for old resident')
    else:need(current['boot_id']!=SOURCE_IDENTITY['boot_id'],'new boot required for new charger resident')
    return dict(profile=request['profile'],resident_notes=profile['notes'],boot_sha256=BOOT,logdump_sha256=LOGDUMP504,current_version=VERSION504)

def source_paths(transaction):
    need(transaction==SOURCE_TX,'only the prepared current timer stage')
    root=ROOT+'/'+transaction
    names={'request':'request-private.json','stage_source':'stage-worker.py','wrapper':'worker.py','supervisor':'supervisor.py',
           'launch':'launch-private.json','supervisor_launch':'supervisor-launch-private.json','supervisor_process':'supervisor-process-private.json',
           'worker_process':'worker-process-private.json','worker_terminal':'worker-terminal-private.json',
           'stage_process':'device-stage/process-private.json','result':'device-stage/result.json','before':'device-stage/before-private.json',
           'stopped':'device-stage/stopped-private.json','after':'device-stage/after-private.json','files_before':'device-stage/files-before-private.json',
           'old_charger':'device-stage/samurai-mp2650.ko.before','old_manifest':'device-stage/manifest.json.before'}
    return {name:root+'/'+relative for name,relative in names.items()}

def process_observation(receipt):
    root=Path('/proc',str(receipt['pid']))
    try:
        fields=(root/'stat').read_text().rsplit(')',1)[1].split()
        ticks=int(fields[19])
        if ticks!=receipt['startticks']:return dict(state='pid_reused_source_ended',pid=receipt['pid'])
        return dict(state='zombie' if fields[0]=='Z' else 'live_original',pid=receipt['pid'],startticks=ticks)
    except FileNotFoundError:return dict(state='absent',pid=receipt['pid'])

def source_processes(request,records):
    if request['identity']['boot_id']!=SOURCE_IDENTITY['boot_id']:
        return {role:dict(state='source_boot_ended',source_boot_id=SOURCE_IDENTITY['boot_id'],current_boot_id=request['identity']['boot_id']) for role in ['worker','supervisor']}
    return {role:process_observation(records[role+'_process']) for role in ['worker','supervisor']}

def verify_source_records(request,raws,processes):
    projection=request['source_stage'];paths=source_paths(projection['transaction_id'])
    need(set(projection)=={'transaction_id','evidence'} and set(projection['evidence'])==set(raws)==set(paths),'all seventeen actual source records')
    for name,path in paths.items():
        need(projection['evidence'][name]==dict(path=path,sha256=sha(raws[name])),'exact source path/bytes '+name)
    need(sha(raws['request'])==SOURCE_REQUEST_SHA and sha(raws['stage_source'])==STAGE_WORKER and
         sha(raws['supervisor'])==STAGE_SUPERVISOR and sha(raws['wrapper'])==STAGE_WRAPPER,'fixed executed original request/code')
    binary={'stage_source','wrapper','supervisor','old_charger','old_manifest'}
    records={name:json.loads(raw) for name,raw in raws.items() if name not in binary}
    original=records['request'];result=records['result'];terminal=records['worker_terminal']
    need(original['identity']==SOURCE_IDENTITY and original['worker_sha256']==STAGE_WORKER,'actual prepared source identity')
    need(terminal['terminal'] is True and terminal['returncode']==0 and terminal['receipt_error'] is None and
         terminal['process']==records['worker_process'] and terminal['pid']==records['worker_process']['pid'],'original same-child successful terminal')
    worker,supervisor=records['worker_process'],records['supervisor_process']
    for role,receipt in [('worker',worker),('supervisor',supervisor)]:
        need(set(receipt)=={'pid','startticks','argv'} and type(receipt['pid']) is type(receipt['startticks']) is int and
             receipt['pid']>0 and receipt['startticks']>0,'actual source process identity')
        suffix=['-B',ROOT+'/'+SOURCE_TX+'/'+role+'.py']+(['--supervise',ROOT+'/'+SOURCE_TX] if role=='supervisor' else [])
        need(receipt['argv'][1:]==suffix and receipt['argv'][0] in ['/usr/sbin/python3','/usr/bin/python3'],'fixed source process argv')
    need(records['supervisor_launch']==supervisor and records['launch']==dict(boot_id=SOURCE_IDENTITY['boot_id'],worker_sha256=STAGE_WRAPPER),'original supervisor launch binding')
    stage_process=records['stage_process']
    need(stage_process['pid']==worker['pid'] and stage_process['start_ticks']==worker['startticks'] and
         stage_process['argv']==worker['argv'] and stage_process['boot_id']==SOURCE_IDENTITY['boot_id'] and
         stage_process['transaction_id']==SOURCE_TX,'actual stage ran inside the original child')
    need(result['request_sha256']==SOURCE_REQUEST_SHA and result['cohort_delivery_sha256']==SOURCE_COHORT and
         result['payload_sha256']==FORWARD_PAYLOAD and result['old_manifest_sha256']==OLD_FILES[MANIFEST] and
         result['new_manifest_sha256']==NEW_FILES[MANIFEST],'exact source stage transition')
    need(result['terminal'] and result['staged'] and result['stop_verified'] and result['disk_state']=='all_new_fsynced' and
         result['status']=='staged/runtime_pending' and result['primary_error'] is result['recovery_error'] is None and
         result['activation_attempted'] is result['new_module_loaded'] is result['capture_issued'] is False,'completed cold stage only')
    for name,key in [('old_charger',TARGET),('old_manifest',MANIFEST)]:need(sha(raws[name])==OLD_FILES[key],'actual original backup')
    expected={path:dict(sha256=OLD_FILES[path],mode='0600',bytes=len(raws['old_charger' if path==TARGET else 'old_manifest'])) for path in ORDER}
    need(records['files_before']==expected,'source backup identities/modes')
    # Run the exact original pure archive/snapshot guards against the saved
    # source time frame. No Device is constructed and __main__ is never run.
    ns={'__name__':'authenticated_source_guards'};exec(compile(raws['stage_source'],'retained-timer-stage','exec'),ns)
    files,new=ns['unpack'](original);ns['manifest_delta'](json.loads(raws['old_manifest']),new)
    before,stopped,after=(records[k] for k in ['before','stopped','after'])
    need(all(value['state']['boot_id']==SOURCE_IDENTITY['boot_id'] for value in [before,stopped,after]),'source snapshots belong to the actual source boot')
    ns['time']=SimpleNamespace(CLOCK_BOOTTIME=time.CLOCK_BOOTTIME,clock_gettime=lambda _:before['read_end']+.001)
    need(ns['healthy'](before,True)==result['before_healthy_mode'],'actual original healthy mode')
    ns['time']=SimpleNamespace(CLOCK_BOOTTIME=time.CLOCK_BOOTTIME,clock_gettime=lambda _:stopped['read_end']+.001)
    ns['stopped_snapshot'](before,stopped,stopped['read_end']+.001)
    ns['time']=SimpleNamespace(CLOCK_BOOTTIME=time.CLOCK_BOOTTIME,clock_gettime=lambda _:after['read_end']+.001)
    ns['stopped_snapshot'](stopped,after,after['read_end']+.001)
    need(before['identity']==dict(SOURCE_IDENTITY,guard_sha256=original['adoption']['guard_sha256']) and
         before['notes']==stopped['notes']==after['notes']==OLD_NOTES and result['resident_notes']==OLD_NOTES,'source identity and old resident preserved')
    need(set(processes)=={'worker','supervisor'},'actual source owner observations')
    if request['identity']['boot_id']==SOURCE_IDENTITY['boot_id']:
        for role in processes:
            need(processes[role]['state'] in ['absent','zombie','pid_reused_source_ended'] and processes[role]['pid']==records[role+'_process']['pid'],'no live original source owner')
    else:
        expected=dict(state='source_boot_ended',source_boot_id=SOURCE_IDENTITY['boot_id'],current_boot_id=request['identity']['boot_id'])
        need(processes=={'worker':expected,'supervisor':expected},'never attribute old PIDs in new boot')
    return dict(source_stage_terminal_verified=True,source_result_sha256=sha(raws['result']),source_boot_ended=request['identity']['boot_id']!=SOURCE_IDENTITY['boot_id'],
                original_snapshot_guards_replayed=True,source_process_observations=processes)

def retained(before,after):
    legacy_retained(before,after)
    need(before['current_cache']==after['current_cache'],'same protection instance/cache')
    if before['sample'].get('logical_full')==1 and before['sample'].get('online')==after['sample'].get('online')==1:
        need(after['sample'].get('logical_full')==1 and after['sample'].get('full_cause')==before['sample'].get('full_cause') and
             after['sample'].get('session_seconds')==0,'online Full/cause retained')

def device_source_proof(self,request):
    paths=source_paths(request['source_stage']['transaction_id']);raws={name:read_owned(path)[0] for name,path in paths.items()}
    original=json.loads(raws['request']);guard,mode=read_owned(original['adoption']['guard_path'])
    need(mode==0o600 and guard==(SOURCE_IDENTITY['boot_id']+'\n').encode() and sha(guard)==original['adoption']['guard_sha256'],'retained original guard')
    records={name:json.loads(raws[name]) for name in ['worker_process','supervisor_process']}
    result=verify_source_records(request,raws,source_processes(request,records));self.log('source-proof-private.json',result);return result

Device.source_proof=device_source_proof
