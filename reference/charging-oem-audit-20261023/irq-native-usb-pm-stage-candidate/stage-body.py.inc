COHORT='89349ffc0adb7e0043505f0250b53eefd78cc917f0b953fb12bb4aeabe25da01'
NEW='34ead4cdb98c2d4b812662cdbe4c0964d5e705574b5d4ab85716b37975a8a39b'
PAYLOAD='f1162d2b5614327f0ce78c918cec62fd681d42cca99d8c03819cfa41086230bc'
OLD_FILES={USB:USB_OLD,MANIFEST:OLD}
NEW_FILES={USB:USB_NEW,MANIFEST:NEW}

def unpack(request):
    need(set(request)=={'schema','transaction_id','cohort_delivery_sha256','payload_sha256','payload_base64','worker_sha256','identity','adoption','lease_token'},'request keys')
    need(request['schema']=='samurai-irq-native-usb-pm-stage-request-v1' and re.fullmatch(r'irq-native-usb-pm-stage-[a-z0-9-]{8,48}',request['transaction_id']),'new stage schema/transaction')
    need(request['cohort_delivery_sha256']==COHORT and request['payload_sha256']==PAYLOAD,'fixed real cohort')
    i,a=request['identity'],request['adoption']
    need(set(i)=={'boot_id','version','serial_sha256','compatible_sha256','rootfs_sha256'} and str(uuid.UUID(i['boot_id']))==i['boot_id'] and i['version']==VERSION,'actual current502 identity')
    need(set(a)=={'transaction_id','guard_path','guard_sha256'} and re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}',a['transaction_id']) and
         a['guard_path']=='/var/lib/samurai/'+a['transaction_id']+'-adopted/boot-id-private.txt','actual original IRQ adopted guard')
    for value in [request['worker_sha256'],a['guard_sha256'],i['serial_sha256'],i['compatible_sha256'],i['rootfs_sha256']]:need(isinstance(value,str) and re.fullmatch('[0-9a-f]{64}',value),'actual hash field')
    need(re.fullmatch('[0-9a-f]{48}',request['lease_token']),'unique lease token')
    raw=base64.b64decode(request['payload_base64'],validate=True);need(len(raw)==27163 and sha(raw)==PAYLOAD,'exact actual forward payload')
    files={}
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        members=tar.getmembers();need(len(members)==2,'exact two files')
        for m in members:
            target='/'+m.name
            need(target in ORDER and target not in files and m.name==target.lstrip('/') and m.isfile() and m.mode==0o600 and m.uid==m.gid==0 and m.uname==m.gname=='root' and m.mtime==0 and not m.pax_headers,'fixed member metadata')
            content=tar.extractfile(m).read();need(sha(content)==NEW_FILES[target],'exact member bytes');files[target]=content
    return files,json.loads(files[MANIFEST])

def manifest_delta(old,new):
    expected=copy.deepcopy(old)
    need(old['release']==RELEASE and old['modules']['samurai-usb-input']=={'target':USB,'sha256':USB_OLD},'current IRQ USB identity')
    expected['adapter_revision']='usb-irq-native-pm-budget504-01'
    expected['modules']['samurai-usb-input']['sha256']=USB_NEW;expected['installed_files'][USB]=USB_NEW
    need(new==expected and old['installed_files'][SERVICE]==SERVICE_SHA and old['modules']['samurai-mp2650']['sha256']=='97c16c3dc0b458fa4d2c686912ffdf805b899abfb846201767843a0348cbffdd' and
         old['modules']['samurai-gauge-protection']['sha256']=='7848cfab264dde1f7f02b24b8022b951d4f3a604eba120b313bac23d0f4a3044','only fixed USB hash and cohort revision change')
    need(old['default_input_cap_ua']==900000 and old['default_charge_cap_ua']==250000 and old['source_budget_enforced'] is True,'retained limits policy')

def stopped_snapshot(before,after,now):
    safe_sample(after);source_limits(after);unchanged(before,after)
    need(before['notes']==after['notes']==NOTES and before['source']==after['source'] and before['limits']==after['limits'],'all old live notes/source/limits retained')
    br,ar=before['registers'],after['registers']
    need(set(br)==set(ar) and '14' not in br,'non-destructive register set')
    for key in br:
        if key=='08':need(ar[key]==((br[key]&~0x18)|8),'only INHIBIT control change')
        elif key!='13':need(ar[key]==br[key],'all other configuration retained')
    need(ar['13']&2 and after['sample']['desired_enable']==0,'stopped actual converter/source')
    s=after['sample']
    need(s.get('hold_requested')==s.get('full_holding')==0,'INHIBIT is not Full holding')
    if before['sample'].get('logical_full'):
        need(s.get('logical_full')==1 and s.get('full_cause')==before['sample']['full_cause'] and s.get('session_seconds')==0,'prior logical Full/cause retained while holding clears')
    elif s.get('logical_full'):
        need(s.get('full_cause') in (1,2,3) and s.get('session_seconds')==0,'newly observed genuine Full retained')
    else:need(s.get('full_cause')==0,'nonFull cause remains zero')

def rollback_gate(device,request,before,manager,old):
    # Only file restoration; never new AUTO/load/stop after the original stop.
    need(not device.uncertain,'unknown original process/module state')
    need(device.identity(request)==before['identity'],'same current boot/guard/board')
    device.notes_match(manager,old,backups=True)
    need(device.mac_evidence()==before['mac_evidence'],'same consumed MAC instance/cache')
    need(device.registers()['08']&0x18==8,'known physical INHIBIT before restoring disk')

def stage(request,device,execute=False):
    need(execute,'explicit --execute-stage only')
    result=dict(schema='samurai-irq-native-usb-pm-stage-result-v1',transaction_id=request.get('transaction_id'),request_sha256=sha(device.request_raw),
                cohort_delivery_sha256=COHORT,old_manifest_sha256=OLD,new_manifest_sha256=NEW,payload_sha256=PAYLOAD,
                staged=False,status='not_staged',phase='rejected',runtime_pending=True,terminal=True,stop_verified=False,
                primary_error=None,recovery_error=None,activation_attempted=False,new_module_loaded=False,capture_issued=False)
    phase='request';before=paused=backups=manager=old=None;write_attempted=False
    try:
        files,new=unpack(request);phase='begin';device.begin(request)
        phase='preflight';backups={name:device.read_owned(name) for name in ORDER}
        for name,(raw,mode) in backups.items():need(mode==0o600 and sha(raw)==OLD_FILES[name],'exact current18e8/7cb disk')
        old=json.loads(backups[MANIFEST][0]);manifest_delta(old,new)
        manager=device.manager(SERVICE_SHA);need(device.verify(manager)==old,'fresh original manager verify')
        device.notes_match(manager,old);before=device.observe(manager)
        result['before_healthy_mode']=healthy(before,True);unchanged(before,before);need(before['notes']==NOTES,'current97c/7848/7cb notes')
        device.backup(backups,before);device.check_window(request)
        phase='synchronous-stop';stopped(device,manager,old,result);result['stop_verified']=True
        phase='stopped-proof';paused=device.observe(manager);stopped_snapshot(before,paused,time.clock_gettime(time.CLOCK_BOOTTIME))
        device.log('stopped-private.json',paused)
        for name in ORDER:
            phase='replace-usb' if name==USB else 'replace-manifest'
            device.check_window(request);rollback_gate(device,request,before,manager,old)
            write_attempted=True;device.replace(name,files[name])
        phase='staged-proof';device.check_window(request);need(device.verify(manager)==new,'new disk manager verify only')
        device.notes_match(manager,old,backups=True);after=device.observe(manager)
        stopped_snapshot(paused,after,time.clock_gettime(time.CLOCK_BOOTTIME));device.log('after-private.json',after)
        device.check_window(request)
        result.update(staged=True,phase='staged',status='staged/runtime_pending',resident_notes=after['notes'],configuration='INHIBIT retained',
                      logical_full_retained=after['sample']['logical_full'],full_cause_retained=after['sample']['full_cause'])
    except BaseException as error:
        result.update(primary_error=dict(phase=phase,error=detail(error)),phase='failed',status='failed_inhibited_no_replay')
        if isinstance(error,AtomicFailure):result['primary_error']['atomic_stage']=error.stage
        if write_attempted and result['stop_verified']:
            try:
                rollback_gate(device,request,before,manager,old)
                for name in ORDER:
                    device.replace(name,backups[name][0],restore=True)
                need(device.verify(manager)==old,'exact old disk restored')
                rollback_gate(device,request,before,manager,old)
                result['restored_original_disk']=True;result['status']='failed_old_disk_restored_inhibited'
            except BaseException as recovery_error:result['recovery_error']=detail(recovery_error)
        if device.uncertain:result.update(terminal=False,status='unknown_original_worker_or_module_no_replay')
    finally:
        try:device.finish(result)
        except BaseException as error:result.update(staged=False,phase='failed',status='receipt_failure_inspect_same_worker',receipt_error=detail(error))
        try:device.close()
        except BaseException as error:result.update(staged=False,phase='failed',status='close_failure_inspect_same_worker',close_error=detail(error))
        try:device.publish(result)
        except BaseException as error:result.update(staged=False,phase='failed',status='receipt_failure_inspect_same_worker',receipt_error=detail(error))
    return result

def main():
    parser=argparse.ArgumentParser();group=parser.add_mutually_exclusive_group()
    group.add_argument('--execute-stage',action='store_true');group.add_argument('--preflight',action='store_true');args=parser.parse_args()
    if not (args.execute_stage or args.preflight):
        print(json.dumps(dict(source_only=True,device_accessed=False,runtime_request_created=False)));return 0
    need(not sys.flags.optimize,'nonoptimized Python');os.umask(0o077)
    raw=sys.stdin.buffer.read(120001);need(0<len(raw)<=120000,'bounded explicit request')
    request=json.loads(raw);device=Device(raw)
    try:
        result=preflight(request,device,raw) if args.preflight else stage(request,device,True)
        print(json.dumps(result),flush=True)
    except BaseException:
        if not device.uncertain:raise
        while True:time.sleep(1)
    while device.uncertain:time.sleep(1)
    return 0 if (result.get('passed') if args.preflight else result['staged']) else 1

if __name__=='__main__':raise SystemExit(main())
