from pathlib import Path
import hashlib
import json
import re
import tarfile
r = Path('/mnt/e/RealmeX2Pro edk2')
private = Path('/mnt/e/edk2-samurai-out/kernel134')
archive = private / 'k134-pmic-usb-status-private.tar.gz'
with tarfile.open(archive, 'r:gz') as tf:
    data = {m.name.removeprefix('./'): tf.extractfile(m).read() for m in tf.getmembers() if m.isfile()}
verified = 0
for line in data['SHA256SUMS'].decode().splitlines():
    digest, name = line.split('  ./', 1)
    assert hashlib.sha256(data[name]).hexdigest() == digest
    verified += 1
assert verified == len(data) - 1
op = json.loads(data['operation-validation.json'])
assert op['status_register_reads'] == 56 and op['register_data_writes'] == 0
assert op['typec_role_or_pd_changes'] == op['client_or_driver_rebinding'] == 0
assert op['same_boot'] and op['same_desktop_pids'] and op['taint'] == 0
samples = json.loads(data['status-samples.json'])
expected = dict(zip(['0x1307', '0x1308', '0x1310', '0x1506', '0x1509', '0x150b', '0x150d'],
                    [1, 4, 16, 8, 35, 43, 6]))
assert len(samples) == 8 and all(s['registers'] == expected for s in samples)
for name, count in [('nv-check.txt', 6), ('source-check.txt', 4), ('vendor-check.txt', 1), ('package-check.txt', 2)]:
    lines = data[name].decode().splitlines()
    assert len(lines) == count and all(line.endswith(': OK') for line in lines)
for name in ['phosh', 'phoc']:
    assert data[name + '-before.txt'] == data[name + '-after.txt']
faults = {}
for name, pattern in [('gpu', r'gpu fault'), ('dpu', r'frame_done.*timeout'), ('bt', r'reassembl')]:
    before = len(re.findall(pattern, data['dmesg-before-private.txt'].decode(), re.I))
    after = len(re.findall(pattern, data['dmesg-after-private.txt'].decode(), re.I))
    assert before == after
    faults[name] = dict(before=before, after=after)
debugfs = (private / 'current132--drivers--base--regmap--regmap-debugfs.c').read_text()
spmi = (private / 'current132--drivers--mfd--qcom-spmi-pmic.c').read_text()
assert '.max_register\t= 0xffff' in spmi and '.val_bits\t= 8' in spmi and '.reg_bits\t= 16' in spmi
assert 'if (buf_pos + map->debugfs_tot_len > count)' in debugfs
assert '.llseek = default_llseek' in debugfs and '#undef REGMAP_ALLOW_WRITE_DEBUGFS' in debugfs
assert '.precious_reg' not in spmi and '.readable_reg' not in spmi
report = dict(stage=134, current_kernel=132, archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    verified_members=verified, snapshots=8, samples_identical=True, status_register_values=expected,
    apsd_completed=True, detected_usb_type='CDP', cc_rp='default', legacy_cable=True,
    advertised_bc12_allowance_ua=1500000, allowance_is_not_current_measurement=True,
    declared_gadget_max_power_ma=100, cdp_allowance_independent_of_gadget_descriptor=True,
    usb_remained_configured=op['usb_remained_configured'], individual_status_reads_only=True,
    offset_format_and_count_bound_checked_against_actual_kernel_source=True,
    operation=op, faults=faults, nv_sources_vendor_packages_preserved=True,
    production_usb_supply_deployment_pending=True, charging_control_accepted=False, goal_complete=False)
(r / 'reference/kernel134/pmic-usb-runtime-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('K134_PMIC_STATUS_CAPTURE_AND_CDP_SOURCE_EVIDENCE_VERIFIED', flush=True)
