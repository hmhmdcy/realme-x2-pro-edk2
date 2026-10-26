def load_504_proof():
    # Authenticate actual completed504 artifacts before reading the new Image.
    pins=json.loads(read_bytes(HERE/'Image504-pins.json'))
    if not pins.get('ready'):
        return None
    leaf=HERE.parents[1]/'charging-oem-audit-20261023/dwc-image504-budget-fence-candidate'
    delivery=json.loads(pinned(leaf/'delivery.json',pins['delivery_sha256']))
    records={}
    for name in ['build-result.json','abi-reuse-result.json','execution-receipt.json','owner-result.json']:
        digest=pins['receipts'][name]
        assert delivery['files'][name]['sha256']==digest
        records[name]=json.loads(pinned(leaf/name,digest))
    r=records['build-result.json'];a=records['abi-reuse-result.json'];e=records['execution-receipt.json'];o=records['owner-result.json']
    assert delivery['passed'] and r['passed'] and a['passed'] and e['passed']
    assert r['child_returncode']==0 and r['child_state']['terminal'] and r['child_state']['returncode']==0
    assert r['parent_namespace_unchanged'] and r['parent_mounts_unchanged']
    assert r['shared_before']==r['shared_after'] and r['shared_source_before']==r['shared_source_after']
    assert r['original363_before']==r['original363_after'] and all(r['baseline_trees_preserved'].values())
    assert o['terminal'] and o['returncode']==0 and o['original_exec_session_id']==63242
    assert e['same_original_exec_waited'] and e['parent_terminal'] and e['original_exec_session_id']==63242
    assert e['parent_pid']==o['parent_pid']==545
    assert e['namespace_process']['terminal'] and e['namespace_process']['returncode']==0
    assert e['namespace_process']['pid']==o['namespace_pid']==1393
    assert r['child_state']['child_pid']==o['make_children'][-1]['pid']==1958
    assert all(x['terminal'] and x['returncode']==0 for x in o['make_children'])
    build=r['build'];compat=build['compatibility']
    assert build['passed'] and compat['passed'] and build['B_default_false_unchanged']
    assert build['source_sha256']=='0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b'
    assert build['dwc_sources']==delivery['source_changes']==pins['DWC_sources']
    assert build['unchanged_other_leaf_count']==3241 and build['unchanged_libstub_count']==32
    assert build['initramfs_unchanged'] and build['config_exact_original'] and build['release_unchanged']
    assert compat['actual_ELF_export_names_exact_502'] and compat['builtin_export_rows_exact_502']
    assert compat['Module_symvers_exact_502'] and compat['public_headers_unchanged']
    assert compat['archive_order_exact'] and not compat['diagnostics']
    assert a['actual_504_comparisons']==compat and all(v==1 for v in a['eight_actual_Kbuild_compiles'].values())
    assert len(a['eight_actual_Kbuild_compiles'])==8
    assert r['identity']['KBUILD_BUILD_VERSION']=='504' and r['identity']['UTS_RELEASE']=='7.3.0-rc6-rmx1931-samurai-k363+'
    assert r['private_output']=='/home/cy122/charging-management-20261023/dwc-image504-budget-fence-01'
    im=build['outputs']['arch/arm64/boot/Image']
    assert im==delivery['outputs']['arch/arm64/boot/Image']
    assert im['sha256']==pins['Image_sha256'] and im['bytes']==pins['Image_bytes']
    assert im['sha256']!='085d03066983a82d1d1c74b74f69c85560698d6fc49f62d6db511a8799b25955'
    return pins

def check_502_carrier_proof():
    leaf=HERE.parents[1]/'charging-session-20261023/gauge-image502-logdump-candidate'
    d=json.loads(pinned(leaf/'delivery.json','eb615331fcb75fbb4cfb21064cea5a8effeffe386ad5ce8839989c7c359420ce'))
    r=json.loads(pinned(leaf/'logdump-result.json','c08d98309b9c789f1f499d08b03ab53c1648c2d5e1efb39359dd7371570e6758'))
    assert d['passed'] and r['passed']
    assert d['candidate']['sha256']=='ace2e261bbfbd923fc3e631e857163f172d09bfb3489f7107782394fbf763ed1'
    assert d['candidate']['bytes']==67108864
    assert d['unchanged_boot_sha256']=='97811cc4ae13b36fec98b2eae7cd54a4f12bca988864df0f3d8f663a8c67f695'
    assert d['FAT_DTB_sha256']=='a82383fa30609bb5e1400f8af12055abdbca7373734c983549d9f437afae2cc5'
    assert r['Image_readback_exact'] and r['all_non_Image_bytes_exact'] and r['fsck_readonly_passed']
    # This authenticates a saved undeployed artifact, not current phone identity.
    return d
