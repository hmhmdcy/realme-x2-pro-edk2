def load_502_proof():
    # No Image access until an explicit frozen author handoff and all receipts.
    pins=json.loads((HERE/'Image502-pins.json').read_bytes())
    if not pins.get('ready'):
        return None
    leaf=HERE.parents[1]/'charging-ui-audit-20261023/gauge-image502-notify-candidate'
    delivery=json.loads(pinned(leaf/'delivery.json',pins['delivery_sha256']))
    records={}
    for name in ['build-result.json','abi-reuse-result.json','execution-receipt.json']:
        digest=pins['receipts'][name]
        assert delivery['files'][name]==digest
        records[name]=json.loads(pinned(leaf/name,digest))
    r=records['build-result.json'];a=records['abi-reuse-result.json'];e=records['execution-receipt.json']
    assert delivery['passed'] and r['passed'] and a['passed'] and e['passed']
    assert r['child_returncode']==0 and r['child_state']['terminal'] and r['child_state']['returncode']==0
    assert r['parent_namespace_unchanged'] and r['parent_mounts_unchanged']
    assert r['shared_before']==r['shared_after'] and r['original363_before']==r['original363_after']
    assert all(r['baseline_trees_preserved'].values())
    assert r['B_source_sha256']==delivery['source_sha256']=='0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b'
    build=r['build'];compat=build['compatibility']
    assert build['passed'] and compat['passed'] and build['B_default_false_unchanged']
    assert build['unchanged_other_leaf_count']==3245 and build['unchanged_libstub_count']==32
    assert [x['path'] for x in build['leaf_delta']]==['drivers/power/supply/bq27xxx_battery.o','init/version.o']
    assert build['initramfs_unchanged'] and build['config_exact_original'] and build['release_unchanged']
    assert compat['actual_ELF_export_names_exact_501'] and compat['builtin_export_rows_exact_501']
    assert compat['Module_symvers_exact_501'] and compat['public_headers_unchanged']
    assert compat['archive_order_exact'] and not compat['diagnostics']
    assert a['new_build_receipt_sha256']==pins['receipts']['build-result.json']
    assert a['actual_502_comparisons']==compat
    assert e['returncode']==0 and e['same_original_exec_handle_waited'] and e['no_live_build_process_remaining']
    assert r['identity']['KBUILD_BUILD_VERSION']=='502' and r['identity']['UTS_RELEASE']=='7.3.0-rc6-rmx1931-samurai-k363+'
    assert r['private_output']=='/home/cy122/charging-management-20261023/gauge-image502-notify-01'
    im=build['outputs']['arch/arm64/boot/Image']
    assert im==delivery['outputs']['arch/arm64/boot/Image']
    assert im['sha256']==pins['Image_sha256'] and im['bytes']==pins['Image_bytes']
    assert pins['Image_sha256']!='3a656c75d3b714153d77b637654c894a0418fd688cc906d59a37a41401e8cc02'
    return pins
