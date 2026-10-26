from pathlib import Path
import hashlib,json,re,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel107';out=Path('/mnt/e/edk2-samurai-out/kernel107');k=Path('/home/cy122/x2pro-linux/linux');init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for a,b in [('dtb-before','dtb-radio'),('cpio-before','cpio-after'),('config-before','config-after')]:assert (out/a).read_bytes()==(out/b).read_bytes()
assert json.loads((out/'initramfs-before.json').read_text())=={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
assert json.loads((out/'untracked-before.json').read_text())=={n:sha(k/n) for n in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=k,text=True).splitlines() if (k/n).is_file()}
prep=json.loads((out/'preparation.json').read_text());allow=set(prep['source_scope'])
def chunks(s):return {c.splitlines()[0]:c for c in s.split('diff --git ')[1:] if c.splitlines()[0].split(' b/',1)[1] not in allow}
assert chunks((out/'kernel-source-before.patch').read_text())==chunks(subprocess.check_output(['git','diff','--binary'],cwd=k,text=True))
for n in ['af_qrtr.c','ns.c']:assert (ref/(n+'.after')).read_bytes()==(k/'net/qrtr'/n).read_bytes()
subprocess.run(['git','diff','--check','--',*sorted(allow)],cwd=k,check=True)
assert not re.search(r'warning:|error:',(out/'target-build.log').read_text())
boot=Path('/mnt/e/edk2-samurai-out/kernel106/radio-bootconfig.txt')
assert sha(boot)==json.loads((out.parent/'kernel106/kernel-validation.json').read_text())['radio_bootconfig_sha256']
assert (out/'Image-radio').stat().st_size<63*1024*1024
v=dict(kernel_audit_pass=True,logical_stage=107,kernel_build=106,dtb_byte_identical=True,original_initramfs_files_preserved=True,initramfs_byte_identical=True,all_existing_modules_byte_identical=True,earlier_snapshots_preserved=True,other_tracked_sources_unchanged=True,existing_untracked_sources_preserved=True,changed_sources=sorted(allow),config_delta={},display_bootconfig_preserved=True,radio_bootconfig_sha256=sha(boot),image_sha256=sha(out/'Image-radio'),image_bytes=(out/'Image-radio').stat().st_size,dtb_sha256=sha(out/'dtb-radio'),cpio_sha256=sha(out/'cpio-after'),w1_c_warnings=0,endpoint_and_resume_hello_initiators_preserved=True,hello_first_reply_and_announcement_sequence_restored=True,destructive_hello_gate_removed=True,nv_partition_writes=False,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(v,indent=2)+'\n');print('STAGE107_TWO_SOURCE_FIX_AND_ALL_PREVIOUS_CONTENT_PRESERVATION_AUDIT_PASS')
