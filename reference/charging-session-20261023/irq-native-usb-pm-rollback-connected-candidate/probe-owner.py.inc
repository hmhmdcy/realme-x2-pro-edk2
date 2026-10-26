def probe(profile,stage_directory,stage_fetch_directory,output,context=None):
    pins,_=source_check();binder=load_module(pins['binder']['path'],'current_rollback_connected_probe_bind')
    code=binder.probe_payload(profile,stage_directory,stage_fetch_directory,context)
    out=local(output).resolve()
    need(out.parent==PRIVATE.resolve() and re.fullmatch(r'probe-[a-z0-9-]{8,48}',out.name) and not out.exists(),'new private current probe output')
    compressed=load_module(pins['profile']['path'],'original_compressed_readonly_owner')
    original=compressed.host_module()
    need(original.transport_argv(original.PEER)==binder.transport_argv(),'original compressed strict-key argv differs')
    mask=os.umask(0o077)
    try:
        PRIVATE.mkdir(mode=0o700,parents=True,exist_ok=True);out.mkdir(mode=0o700)
        compressed.send_readonly(out,code)
        return binder.review_current(profile,stage_directory,stage_fetch_directory,out,context)
    finally:os.umask(mask)
