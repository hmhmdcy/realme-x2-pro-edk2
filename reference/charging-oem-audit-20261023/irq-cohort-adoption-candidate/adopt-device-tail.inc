GUARD_ROOT=Path('/var/lib/samurai')

def adopt_current_irq_boot(adoption):
    assert adoption['schema']=='samurai-usb-irq-protection-adoption-v1'
    tx=adoption['transaction_id']
    assert re.fullmatch(r'usb-irq-protection-activate-[a-z0-9-]{8,48}',tx)
    target=Path(adoption['guard'])
    assert target==GUARD_ROOT/(tx+'-adopted')/'boot-id-private.txt'
    request=adoption['postboot_request']
    fresh={};collect(request,fresh);verified=audit(fresh,request)
    assert verified['passed'] is True and not verified['errors'] and verified['hardware_writes']==0
    assert fresh['identity_before']==fresh['identity_after']
    assert fresh['identity_before']['boot_id']==adoption['boot']
    assert fresh['identity_before']['uname']['version']==adoption['version']=='#502 SMP PREEMPT Tue Oct 20 03:03:47 UTC 2026'
    assert not target.exists() and not target.parent.exists()
    proof={'raw':fresh,'result':verified,'postboot_raw_sha256':adoption['postboot_raw_sha256'],
           'postboot_request_sha256':adoption['postboot_request_sha256'],
           'activation_transaction_id':tx,'stage_transaction_id':adoption['stage_transaction_id']}
    proof_raw=(json.dumps(proof,indent=2)+'\n').encode()
    guard_raw=(adoption['boot']+'\n').encode()
    os.umask(0o077);target.parent.mkdir(mode=0o700)
    # Guard is last; any partial directory is retained and never reopened.
    for name,raw in [('fresh-validation-private.json',proof_raw),('boot-id-private.txt',guard_raw)]:
        with (target.parent/name).open('xb') as file:
            file.write(raw);file.flush();os.fsync(file.fileno())
    fd=os.open(target.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    fd=os.open(target.parent.parent,os.O_RDONLY|os.O_DIRECTORY)
    try:os.fsync(fd)
    finally:os.close(fd)
    assert target.read_bytes()==guard_raw
    actual_proof=(target.parent/'fresh-validation-private.json').read_bytes()
    assert actual_proof==proof_raw
    return {'guard_created':True,'old_guards_preserved':True,'transaction_id':tx,'boot_id':adoption['boot'],
            'guard':str(target),'postboot_raw_sha256':adoption['postboot_raw_sha256'],
            'fresh_validation_passed':True,'fresh_validation_sha256':hashlib.sha256(actual_proof).hexdigest(),
            'guard_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),
            'cohort_verified':True,'charging_controls_written':False,'hardware_writes':0}

print(json.dumps(adopt_current_irq_boot(ADOPTION)),flush=True)
