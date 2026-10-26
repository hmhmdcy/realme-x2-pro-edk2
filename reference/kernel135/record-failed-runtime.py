from pathlib import Path
import json
import tarfile
import hashlib
import sys
r = Path('/mnt/e/RealmeX2Pro edk2')
out = Path('/mnt/e/edk2-samurai-out/kernel135')
with tarfile.open(out / 'first-runtime-private.tar.gz') as tf:
    data = {}
    for m in tf:
        assert not m.issym() and not m.islnk() and not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
        if m.isfile():
            name = m.name.removeprefix('./')
            assert name not in data
            data[name] = tf.extractfile(m).read()
for l in data['SHA256SUMS'].decode().splitlines():
    h, n = l.split('  ', 1)
    assert hashlib.sha256(data[n.removeprefix('./')]).hexdigest() == h
sys.path.insert(0, str(r / 'reference/kernel113'))
from inspect_live_fdt import fdt
expected = fdt((out / 'DTB-k135-private').read_bytes())
live = fdt(data['live-fdt-private.dtb'])
assert expected.keys() == live.keys()
assert all(all(live[n].get(k) == v for k,v in props.items()) for n,props in expected.items())
before = (out / 'source-boot-id-private.txt').read_bytes().strip()
assert data['boot-id-private.txt'].strip() != before
(out / 'failed-boot-id-private.txt').write_bytes(data['boot-id-private.txt'])
parts = dict((n,h) for h,n in (l.split('  ',1) for l in data['partition-check.sha256'].decode().splitlines()))
package = json.loads((out / 'boot-package-validation.json').read_text())
assert parts['/dev/sde11'] == package['boot_sha256'] and parts['/dev/sde32'] == package['logdump_sha256']
assert parts['/dev/sda2'] == '7e085ef3264e212da7009099113b86ad1f6ec44176840f03f9b85d0e632412f3'
with tarfile.open(out.parent / 'kernel112/layout-after.tar') as tf:
    layout = {m.name.removeprefix('./'):tf.extractfile(m).read() for m in tf if m.isfile()}
for dev in ['sda','sdb','sdc','sdd','sde','sdf']:
    for suffix in ['geometry','head','tail']:
        assert data[dev+'.'+suffix] == layout[dev+'.'+suffix]
for name,count in [('nv-check.txt',6),('source-check.txt',4),('vendor-check.txt',1),('gui-config-check.txt',3)]:
    assert data[name].count(b': OK') == count and b'FAILED' not in data[name]
assert data['full-module-check.txt'].count(b': OK') >= 770 and b'FAILED' not in data['full-module-check.txt']
dmesg = data['dmesg.txt']
report = dict(stage=135, dt_variant=135, software_generation=134, new_boot_verified=True,
    boot_logdump_readback_exact=True, live_dtb_all_nodes_and_properties_verified=True,
    mdss_core_reset_present_in_actual_live_dtb=True, gpt18_persist_and_11_sources_preserved=True,
    all_matching134_modules_verified=True, original_gui_configuration_unchanged=True,
    taint=int(data['state.txt'].splitlines()[-1]), phosh_running=bool(data['phosh.txt'].strip()),
    phoc_running=bool(data['phoc.txt'].strip()), display_connected=data['connector.txt'].strip()==b'connected',
    drm_resolved=data['drm-resolved.txt'].decode().strip(),
    original_ctl_reset_failure_count=dmesg.count(b'CTL shutdown failed'),
    original_kms_init_failure_count=dmesg.count(b'kms hw init failed'),
    wcd934x_probe_warn=dmesg.count(b'at wcd934x_comp_probe'),
    dsi_clock_disable_warn=dmesg.count(b'at clk_core_disable'),
    dsi_clock_unprepare_warn=dmesg.count(b'at clk_core_unprepare'),
    slimbus_dma_error_count=dmesg.count(b'Failed to prepare DMA'),
    codec_enospc_count=dmesg.count(b'ASoC error (-28)'),
    gpu_fault_events=dmesg.count(b'*** gpu fault'), dpu_timeout_events=dmesg.count(b'frame done timeout'),
    initial_display_boot_pass=False, candidate_rejected=True, permanent_display_fix=False,
    mdss_reset_absence_as_root_cause_unproven=True, rollback_required=True, rollback_target=132,
    archive_sha256=hashlib.sha256((out / 'first-runtime-private.tar.gz').read_bytes()).hexdigest(),
    hardware_complete=False, goal_complete=False)
assert report['taint'] == 512 and not report['phosh_running'] and not report['phoc_running']
(r / 'reference/kernel135/failed-runtime-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report), flush=True)
