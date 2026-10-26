def rollback_probe(parameters):
    need(set(parameters)=={'transaction_id','worker_sha256','lease_token','payload_base64'},'read-only probe parameters')
    compatible=Path('/sys/firmware/devicetree/base/compatible').read_bytes()
    first=dict(boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),version=os.uname().version,
               serial_sha256=sha(Path('/sys/devices/soc0/serial_number').read_bytes()),compatible_sha256=sha(compatible),
               rootfs_sha256=sha(read_owned('/etc/samurai-rootfs-release')[0]))
    need(os.geteuid()==0 and not sys.flags.optimize and os.uname().release==RELEASE and os.uname().machine=='aarch64' and
         b'realme,samurai' in compatible.split(b'\0'),'original-key actual root/board/kernel probe')
    notes={name:sha(Path('/sys/module',name.replace('-','_'),'notes/.note.gnu.build-id').read_bytes()) for name in OLD_NOTES}
    if first==SOURCE_IDENTITY and notes==OLD_NOTES:profile=PROFILES[0]
    else:
        need(first['boot_id']!=SOURCE_IDENTITY['boot_id'] and notes==NEW_NOTES,'known current new-boot/new-charger tuple')
        profile=PROFILES[1]
    need(Path('/sys/module/samurai_usb_input/parameters/native_retained').read_text().strip()=='Y','retain native USB owner')
    paths=source_paths(SOURCE_TX);raws={name:read_owned(path)[0] for name,path in paths.items()}
    projection=dict(transaction_id=SOURCE_TX,evidence={name:dict(path=path,sha256=sha(raws[name])) for name,path in paths.items()})
    class ProbeDevice(Device):
        def log(self,name,value):pass  # Explicitly no phone-side evidence directory.
    device=ProbeDevice()
    try:
        import fcntl
        device.lock=os.open(LOCK,os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        info=os.fstat(device.lock)
        need(stat.S_ISREG(info.st_mode) and info.st_uid==0 and stat.S_IMODE(info.st_mode)==0o600,'existing protected service lock')
        fcntl.flock(device.lock,fcntl.LOCK_SH|fcntl.LOCK_NB)
        p=Path(INSTANCE);need((p/'driver').resolve().as_posix()=='/sys/bus/platform/drivers/samurai-gauge-protection','actual protection owner')
        device.mac_fd=os.open(p/'mac_evidence',os.O_RDONLY|os.O_CLOEXEC|os.O_NOFOLLOW)
        held=os.fstat(device.mac_fd);raw=os.read(device.mac_fd,16384)
        cache=dict(sha256=sha(raw),raw_base64=base64.b64encode(raw).decode(),attribute_dev=held.st_dev,attribute_inode=held.st_ino,instance_inode=p.stat().st_ino)
        validate_cache(cache)
        request=dict(schema='samurai-charger-timer-cold-rollback-request-v1',transaction_id=parameters['transaction_id'],profile=profile,
            identity=first,source_identity=SOURCE_IDENTITY,source_stage=projection,current_cache=cache,
            payload_sha256=ROLLBACK_PAYLOAD,payload_base64=parameters['payload_base64'],worker_sha256=parameters['worker_sha256'],lease_token=parameters['lease_token'])
        unpack(request);device.request=request
        receipts={name:json.loads(raws[name]) for name in ['worker_process','supervisor_process']}
        observed=source_processes(request,receipts)
        proof=verify_source_records(request,raws,observed)
        original=json.loads(raws['request']);guard,mode=read_owned(original['adoption']['guard_path'])
        need(mode==0o600 and guard==(SOURCE_IDENTITY['boot_id']+'\n').encode() and sha(guard)==original['adoption']['guard_sha256'],'actual retained source guard')
        current=device.current(request);validate_profile(request,current)
        manager=device.manager();device.verify_retained(manager)
        snapshot=device.observe(manager);safe_electrical(snapshot,device.now());idle(snapshot)
        need(snapshot['notes']==expected_profile(request)['notes'],'actual current source notes')
        final=device.current(request,carriers=False);validate_profile(request,final)
        need(first==final['identity'] and current['current_cache']==final['current_cache']==snapshot['current_cache'],'read-only identity/cache bracket')
        return dict(passed=True,eligible=True,read_only=True,phone_directory_or_lease_created=False,request=request,
                    current=final,snapshot=snapshot,source_proof=proof,source_process_observations=observed,
                    source_raws={name:dict(sha256=sha(raw),base64=base64.b64encode(raw).decode()) for name,raw in raws.items()})
    finally:device.close()

print(json.dumps(rollback_probe(PARAMETERS)))
