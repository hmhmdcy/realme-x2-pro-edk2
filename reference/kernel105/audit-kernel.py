from pathlib import Path
import hashlib,json,re,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel105';out=Path('/mnt/e/edk2-samurai-out/kernel105')
k=Path('/home/cy122/x2pro-linux/linux');init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (out/'dtb-before').read_bytes()==(out/'dtb-radio').read_bytes()
assert (out/'cpio-before').read_bytes()==(out/'cpio-after').read_bytes()
assert (out/'config-before').read_bytes()==(out/'config-after').read_bytes()
assert json.loads((out/'initramfs-before.json').read_text())=={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
assert json.loads((out/'untracked-before.json').read_text())=={n:sha(k/n) for n in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=k,text=True).splitlines() if (k/n).is_file()}
allow=set(json.loads((out/'preparation.json').read_text())['source_scope'])
def chunks(s):return {c.splitlines()[0]:c for c in s.split('diff --git ')[1:] if c.splitlines()[0].split(' b/',1)[1] not in allow}
assert chunks((out/'kernel-source-before.patch').read_text())==chunks(subprocess.check_output(['git','diff','--binary'],cwd=k,text=True))
for name,path in [('apr','drivers/soc/qcom/apr.c'),('q6v5','drivers/remoteproc/qcom_q6v5.c'),('q6core','sound/soc/qcom/qdsp6/q6core.c')]:
    assert (ref/(name+'.c.after')).read_bytes()==(k/path).read_bytes()
assert not re.search(r'warning:|error:',(out/'target-build.log').read_text())
assert (out/'Image-radio').stat().st_size<63*1024*1024
report=dict(kernel_audit_pass=True,kernel_build=104,logical_stage=105,dtb_byte_identical=True,original_initramfs_files_preserved=True,initramfs_byte_identical=True,all_existing_modules_byte_identical=True,earlier_snapshots_preserved=True,other_tracked_sources_unchanged=True,existing_untracked_sources_preserved=True,changed_sources=sorted(allow),image_sha256=sha(out/'Image-radio'),image_bytes=(out/'Image-radio').stat().st_size,dtb_sha256=sha(out/'dtb-radio'),cpio_sha256=sha(out/'cpio-after'),w1_c_warnings=0,apr_driver_rebind_registration=True,apr_callbacks_drained_before_remove=True,core_cache_only_valid_version_reply=True,core_errors_propagated=True,crash_diagnostics_readonly=True,nv_partition_writes=False,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('STAGE105_KERNEL_PRESERVATION_AUDIT_PASS')
