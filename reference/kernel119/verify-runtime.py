from pathlib import Path
import json,hashlib,tarfile,re
out=Path('/mnt/e/edk2-samurai-out/kernel119');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel119')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):
    with tarfile.open(p) as tf:d={m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
    for line in d['SHA256SUMS'].decode().splitlines():
        digest,name=line.split('  ',1);assert hashlib.sha256(d[name.removeprefix('./')]).hexdigest()==digest
    return d
assert sha(out/'first-runtime-private.tar.gz')=='32e1078a66d5d78d65e384cff6dbe6bb44f544064582814998c7a580ea33d36b'
d=load(out/'first-runtime-private.tar.gz');before=load(out/'preflash.tar')
assert d['boot-id-private.txt']!=before['boot-id-private.txt']
assert b'#118 SMP PREEMPT' in d['uname.txt'] and d['state.txt'].splitlines()[-1]==b'0'
for dev in ('sda','sdb','sdc','sdd','sde','sdf'):
    for suffix in ('geometry','head','tail'):assert d[f'{dev}.{suffix}']==before[f'{dev}.{suffix}']
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1)]:assert d[name].count(b': OK')==count and b'FAILED' not in d[name]
assert d['sensors.txt'].strip()==b'offline\nvdd=0 vddio=0'
assert d['ipa-module.sha256'].decode().split()[0]=='bdd85687f4889cfe78ca7dbcd8974618fc1a523d65b4d3678f6800a42ceb2ce0'
package=json.loads((out.parent/'kernel118/candidate-package-validation.json').read_text())
parts=dict(line.split('  ')[::-1] for line in d['partition-check.sha256'].decode().splitlines())
assert parts['/dev/sde11']==package['boot_115_sha256'] and parts['/dev/sde32']==package['logdump_sha256']
assert parts['/dev/sda2']=='7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
log=d['dmesg.txt'].decode()
assert 'Initialized msm' in log and 'IPA driver setup completed successfully' in log
assert 'kms hw init failed' not in log and 'SW_RESET still pending' not in log
assert '*** gpu fault' not in log and 'WARNING: drivers/net/ipa/reg.h:87' not in log
(out/'current-boot-id-private.txt').write_bytes(d['boot-id-private.txt'])
traces=load(out/'boot-traces-private.tar.gz')
assert sha(out/'boot-traces-private.tar.gz')=='93882196ede6483798fde925a4c565cfbcd67a7e0bba1dbc981a36da0af4cbf2'
assert traces['taint.txt'].strip()==b'0'
report=dict(kernel_build=118,new_boot_verified=True,boot_115_unchanged=True,logdump_118_exact=True,persist_gpt18_nv6_source4_vendor_preserved=True,ipa_fixed_module_preserved=True,taint=0,msm_drm_initialized=True,actual_drm_card='card1',collector_card0_fields_invalid_for_this_boot=True,early_phosh_captured=bool(d['phosh.txt'].strip()),early_phoc_captured=bool(d['phoc.txt'].strip()),rcu_boot_stalls=log.count('rcu_preempt detected stalls'),ctl_reset_failures=log.count('SW_RESET still pending'),kms_bind_failures=log.count('kms hw init failed'),dpu_timeouts=log.count('frame done timeout'),gpu_faults=log.count('*** gpu fault'),ipa_register_warnings=0,ipa_initialized=True,zram_active=b'/dev/zram0' in d['swaps.txt'],slpi_offline_sensor_power_off=True,boot_traces_preserved_and_stopped=True,trace_archive_sha256=sha(out/'boot-traces-private.tar.gz'),native_archive_sha256=sha(out/'first-runtime-private.tar.gz'),later_gui_and_stability_audit_required=True,persistent_display_fix_not_proven=True,goal_complete=False)
for folder in [out,ref]:(folder/'first-runtime-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
