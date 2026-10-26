from pathlib import Path
import hashlib, json, zipfile

root = Path('/mnt/e/edk2-samurai-out/rx61')
prep = json.loads((root / 'source-preparation.json').read_text())
source = Path(prep['source_directory'])
sha = lambda data: hashlib.sha256(data).hexdigest()
archive = root / 'qcom-14b6fe1-source.zip'
assert sha(archive.read_bytes()) == 'ed5b4309139a286f3ef22ad846495bd7dbcb879dce4b4fa66e1d54d3663641a9'
module_hashes = {}
with zipfile.ZipFile(archive) as z:
    prefix = z.namelist()[0]
    for p in sorted((source / 'src/windows/wdfserial').glob('*.c')):
        old = z.read(prefix + 'src/windows/wdfserial/' + p.name)
        data = p.read_bytes()
        changed = data != old
        assert changed == (p.name == 'QCPNP.c')
        module_hashes[p.name] = {'upstream_sha256': sha(old), 'candidate_sha256': sha(data), 'changed': changed}
    assert len(module_hashes) == 9
    baseline = z.read(prefix + 'src/windows/wdfserial/QCPNP.c')
    candidate = (source / 'src/windows/wdfserial/QCPNP.c').read_bytes()
    anchor = b'VOID QCPNP_EvtFileClose'
    assert candidate[candidate.index(anchor):] == baseline[baseline.index(anchor):]
    inf = z.read(prefix + 'src/windows/wdfserial/qcwdfser.inf')
    assert b'9505' not in inf.upper() and b'EUD' not in inf.upper()
report = {
    'commit': '14b6fe1ee69cdd9182502629da9192156b9d206a', 'source_zip_sha256': sha(archive.read_bytes()),
    'all_nine_module_provenance_checked': True, 'module_hashes': module_hashes,
    'all_functions_after_filecreate_unchanged': True, 'upstream_inf_has_eud_match': False,
    'review': [
        'QCPNP_ConfigUsbDevice: bulk IN and OUT without interrupt -> DEVICETYPE_SERIAL; maximum packet size checks disabled.',
        'QCSER_SetModemConfig/GetModemConfig/SerialClrDtr/SerialClrRts: serial branch updates local state; CDC transfers confined to CDC branch.',
        'QCSER_GetStats supports SERIALPERF_STATS; terminal read-only counters remain available in principle.',
        'QCPNP_EvtDeviceD0Entry restarts worker events; it contains no ResetUsbPipe call.',
        'QCRD file close cancels sent I/O through WdfIoTargetStop; preparation resets and recovery behavior remain upstream.',
        'QCWT still adds a ZLP to writes that are a multiple of maximum packet size; no ZLP behavior change in this candidate.',
        'EvtDeviceFileCreate is documented PASSIVE_LEVEL, compatible with its new registry lookup.'
    ],
    'sources': [
        'https://github.com/qualcomm/qcom-usb-kernel-drivers/tree/14b6fe1ee69cdd9182502629da9192156b9d206a',
        'https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/wdfdevice/nc-wdfdevice-evt_wdf_device_file_create',
        'https://learn.microsoft.com/en-us/windows-hardware/drivers/wdf/specifying-wdf-directives-in-inf-files',
        'https://learn.microsoft.com/en-us/windows-hardware/drivers/develop/run-from-driver-store'
    ],
    'limits': 'Read-only source and package review, not driver loading or hardware validation.'
}
(root / 'source-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'modules': len(module_hashes), 'changed': ['QCPNP.c'], 'upstream_eud_inf_match': False, 'source_review': 'PASS'}))
