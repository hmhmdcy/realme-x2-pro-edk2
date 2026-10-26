def probe(rollback_directory,rollback_fetch_directory,output):
    code=probe_payload(rollback_directory,rollback_fetch_directory)
    out=sources.local(output).resolve()
    sources.need(out.parent==PRIVATE.resolve() and re.fullmatch(r'probe-[a-z0-9-]{8,48}',out.name) and not out.exists(),'new private post-restore probe')
    compressed=sources.load('compressed_profile');original=compressed.host_module()
    binder=sources.load('rollback_binder')
    sources.need(original.transport_argv(original.PEER)==binder.transport_argv(),'original strict compressed probe argv')
    mask=os.umask(0o077)
    try:
        PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True);out.mkdir(mode=0o700)
        compressed.send_readonly(out,code)
        return proof.review_completed(rollback_directory,rollback_fetch_directory,out)
    finally:os.umask(mask)

def run(action,transaction,execute=False,window_confirmed=False,*,private=None,start=None):
    # Setting module.PRIVATE cannot change the original run function's bound
    # default argument. Always pass this adapter's actual directory explicitly.
    options={'private':PRIVATE if private is None else sources.local(private)}
    if start is not None:options['start']=start
    return owner().run(action,transaction,execute,window_confirmed,**options)
