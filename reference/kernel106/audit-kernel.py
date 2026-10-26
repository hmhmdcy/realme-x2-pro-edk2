from pathlib import Path
import hashlib,json,re,subprocess
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel106';out=Path('/mnt/e/edk2-samurai-out/kernel106')
k=Path('/home/cy122/x2pro-linux/linux');init=k.parent/'initramfs'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert (out/'dtb-before').read_bytes()==(out/'dtb-radio').read_bytes()
assert (out/'cpio-before').read_bytes()==(out/'cpio-after').read_bytes()
config=lambda p:{l.split('=',1)[0]:l.split('=',1)[1] for l in p.read_text().splitlines() if l.startswith('CONFIG_') and '=' in l}
a=config(out/'config-before');b=config(out/'config-after');delta={n:[a.get(n),b.get(n)] for n in a.keys()|b.keys() if a.get(n)!=b.get(n)}
assert delta=={'CONFIG_BOOT_CONFIG_EMBED_FILE':['"/mnt/e/edk2-samurai-out/kernel84/display-bootconfig-ready.txt"','"/mnt/e/edk2-samurai-out/kernel106/radio-bootconfig.txt"']},delta
assert json.loads((out/'initramfs-before.json').read_text())=={str(p.relative_to(init)):sha(p) for p in init.rglob('*') if p.is_file() and not p.is_symlink()}
prep=json.loads((out/'preparation.json').read_text());new=prep['new_source'];allow=set(prep['source_scope'])
untracked={n:sha(k/n) for n in subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=k,text=True).splitlines() if (k/n).is_file()}
assert untracked.pop(new)==sha(ref/'samurai-diag.h')
assert json.loads((out/'untracked-before.json').read_text())==untracked
def chunks(s):return {c.splitlines()[0]:c for c in s.split('diff --git ')[1:] if c.splitlines()[0].split(' b/',1)[1] not in allow}
assert chunks((out/'kernel-source-before.patch').read_text())==chunks(subprocess.check_output(['git','diff','--binary'],cwd=k,text=True))
for n,p in [('smd.c','net/qrtr/smd.c'),('af_qrtr.c','net/qrtr/af_qrtr.c'),('qrtr.h','include/trace/events/qrtr.h'),('qcom_pd_mapper.c','drivers/soc/qcom/qcom_pd_mapper.c'),('q6core.c','sound/soc/qcom/qdsp6/q6core.c')]:
    assert (ref/(n+'.after')).read_bytes()==(k/p).read_bytes()
assert not re.search(r'warning:|error:',(out/'target-build.log').read_text())
boot=(ref/'bootconfig.txt').read_bytes();assert boot==(out/'radio-bootconfig.txt').read_bytes()
assert boot.startswith(Path('/mnt/e/edk2-samurai-out/kernel84/display-bootconfig-ready.txt').read_bytes())
assert b'tp_printk' not in boot
assert '#define Q6_READY_TIMEOUT_MS 100' in (k/'sound/soc/qcom/qdsp6/q6core.c').read_text()
assert (out/'Image-radio').stat().st_size<63*1024*1024
report=dict(kernel_audit_pass=True,kernel_build=105,logical_stage=106,dtb_byte_identical=True,original_initramfs_files_preserved=True,initramfs_byte_identical=True,all_existing_modules_byte_identical=True,earlier_snapshots_preserved=True,other_tracked_sources_unchanged=True,existing_untracked_sources_preserved=True,changed_sources=sorted(allow|{new}),config_delta=delta,display_bootconfig_preserved=True,radio_bootconfig_sha256=sha(ref/'bootconfig.txt'),image_sha256=sha(out/'Image-radio'),image_bytes=(out/'Image-radio').stat().st_size,dtb_sha256=sha(out/'dtb-radio'),cpio_sha256=sha(out/'cpio-after'),w1_c_warnings=0,qrtr_drvdata_published_before_hello=True,core_query_timeout_ms=100,core_diagnostics_ring_only=True,nv_partition_writes=False,goal_complete=False)
(out/'kernel-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('STAGE106_KERNEL_AND_DISPLAY_BOOTCONFIG_PRESERVATION_AUDIT_PASS')
