def post_probe_request(request, result_sha, saved_binding_sha):
    binding=dict(purpose='after-successful-current-two-file-restore',rollback_transaction_id=request['transaction_id'],
        rollback_request_sha256=sha(encode(request)),rollback_result_sha256=result_sha,host_binding_sha256=saved_binding_sha)
    return dict(schema='samurai-irq-native-usb-pm-rollback-current-probe-v1',new_endpoint=PEER,profile=request['profile'],
        saved_source_binding_sha256=sha(encode(binding)))

def make_guard(tx, token, review):
    import sources
    need(re.fullmatch(TX_PATTERN,tx) and re.fullmatch('[0-9a-f]{48}',token),'new rollback restart identity')
    request=review['request'];current=review['current'];identity=review['identity']
    need(tx!=request['transaction_id'] and identity==current['identity']==request['identity'],'independent same-current-boot restart')
    worker=sources.load('rollback_worker');worker.validate_profile(request,current)
    return dict(schema='samurai-irq-native-usb-pm-rollback-restart-v1',transaction_id=tx,token=token,
        boot_id=identity['boot_id'],kernel_release=RELEASE,kernel_version=identity['version'],
        soc_serial_sha256=identity['serial_sha256'],compatible_sha256=identity['compatible_sha256'],rootfs_release_sha256=identity['rootfs_sha256'],
        profile=request['profile'],current_boot_sha256=current['boot']['sha256'],current_logdump_sha256=current['logdump']['sha256'],
        unchanged_boot_sha256=BOOT,rollback_logdump_sha256=LOGDUMP,boot_bytes=100663296,logdump_bytes=67108864,
        resident_notes=current['notes'],current_cache=current['current_cache'],rollback=review['rollback'],post_restore_probe=review['post_restore_probe'],
        partitions=['logdump'],disk_state='all_original_fsynced',runtime_validation_accepted=False)
