from pathlib import Path
import runpy,tarfile,json,hashlib
root=Path('/mnt/e/RealmeX2Pro edk2');ref=root/'reference/kernel124';out=Path('/mnt/e/edk2-samurai-out/kernel124')
def modules(stage):
    path=Path(f'/mnt/e/edk2-samurai-out/kernel{stage}/modules-k{stage}-private.tar.gz')
    with tarfile.open(path) as tf:return {m.name:hashlib.sha256(tf.extractfile(m).read()).hexdigest() for m in tf if m.isfile() and m.name.endswith('.ko')}
a=modules(123);b=modules(124);assert a.keys()==b.keys() and len(a)==770
changes=[p.split('/kernel/',1)[-1] for p in a if a[p]!=b[p]]
assert 'drivers/media/platform/qcom/camss/qcom-camss.ko' in changes
ipa=[p for p in b if p.endswith('/net/ipa/ipa.ko')];assert len(ipa)==1 and b[ipa[0]]=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
report=dict(modules=770,changed_vs123=changes,all_unchanged_modules_byte_equal=True,fixed_ipa_preserved=True,candidate124_not_runtime118_compatible_claim=True)
(ref/'module-comparison-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
lines=(out/'runtime-health-final-private.txt').read_text().splitlines()
assert lines[0].startswith('#118 SMP PREEMPT') and lines[1:6]==['0','3492','3190','2','1']
assert lines[6:8]==['closed','closed'] and sum(l.endswith(': OK') for l in lines)==11
assert all('powered=0 muted=1' in line and 'failed=0' in line for line in lines[8:10])
assert 'offline' in lines[10:12] and any('vdd=0' in l and 'vddio=0' in l for l in lines)
report=dict(current_kernel=118,same_boot_guard_pass=True,taint=0,phosh_phoc_original_pids_alive=True,dpu_timeouts=2,gpu_faults=1,pcm_closed_amps_idle=True,slpi_offline_power_zero=True,nv6_source4_vendor1_hash_pass=True,no_phone_mutations_this_phase=True,goal_complete=False)
(ref/'runtime-health-validation.json').write_text(json.dumps(report,indent=2)+'\n');print('PHONE118_SAME_BOOT_UNCHANGED_HEALTH_11_HASH_PASS')
