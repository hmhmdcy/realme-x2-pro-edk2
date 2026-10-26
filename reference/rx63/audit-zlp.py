"""Read exact built source to locate the separate ZLP option and its load phase."""
from pathlib import Path
import hashlib
import json
import re

source = Path('/mnt/e/edk2-samurai-out/rx61/source-pinned/qcom-usb-kernel-drivers-14b6fe1ee69cdd9182502629da9192156b9d206a/src/windows/wdfserial')
out = Path('/mnt/e/edk2-samurai-out/rx63/zlp-source-audit.json')
assert not out.exists()
pnp_bytes = (source / 'QCPNP.c').read_bytes()
write_bytes = (source / 'QCWT.c').read_bytes()
assert hashlib.sha256(pnp_bytes).hexdigest() == '7cf3f3db7878d4a1a037da075e4dfda6985851b7805a42434cf3ae2202c014fd'
assert hashlib.sha256(write_bytes).hexdigest() == '06d9235e67fd670ef23c9180b2069b43928bc94db9f946874099f8b1367e1d9a'
pnp = pnp_bytes.decode('utf-8')
write = write_bytes.decode('utf-8')
# Comments/strings do not contribute braces to function-body extraction.
lex = re.compile(r'/\*.*?\*/|//[^\n]*|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', re.S)
plain = lambda text: lex.sub(lambda m: ''.join('\n' if c == '\n' else ' ' for c in m.group()), text)
def function(text, name):
    scrubbed = plain(text)
    match = re.search(r'\b'+re.escape(name)+r'\s*\([^;{]*\)\s*\{', scrubbed)
    assert match, name
    start = scrubbed.index('{', match.start())
    level = 1
    for pos in range(start+1, len(scrubbed)):
        level += (scrubbed[pos] == '{') - (scrubbed[pos] == '}')
        if level == 0:
            return text[match.start():pos+1], text.count('\n', 0, match.start())+1
    raise AssertionError('Unclosed function')
add, add_line = function(pnp, 'QCPNP_EvtDeviceAdd')
opened, open_line = function(pnp, 'QCPNP_EvtFileCreate')
registry, registry_line = function(pnp, 'QCPNP_VendorRegistryProcess')
worker, worker_line = function(write, 'QCWT_WriteRequestHandlerThread')
assert 'QCPNP_VendorRegistryProcess(pDevContext)' in add
assert 'QCPNP_VendorRegistryProcess' not in opened
assert 'QCPNP_EudPreserveToggleOnOpen(pDevContext)' in opened
assert 'PLUGPLAY_REGKEY_DRIVER' in registry
assert 'enableZeroLengthPacket > 0' in registry
assert 'gVendorConfig.EnableZeroLengthPacket = FALSE;' in registry
condition = 'gVendorConfig.EnableZeroLengthPacket && (pDevContext->wMaxPktSize != 0) && (writeParam.Parameters.Write.Length % pDevContext->wMaxPktSize == 0)'
assert condition in worker
assert worker.index('QCWT_EvtIoWrite(') < worker.index(condition) < worker.index('QCWT_SendUsbShortPacket(pDevContext)')
historical = Path('/mnt/e/RealmeX2Pro edk2/reference/rx52/usb-overlap-02.json')
usb = json.loads(historical.read_text())
def collect_endpoints(value):
    records=[]
    if isinstance(value, dict):
        if 'max_packet' in value: records.append(value)
        for x in value.values(): records += collect_endpoints(x)
    elif isinstance(value,list):
        for x in value: records += collect_endpoints(x)
    return records
endpoints = collect_endpoints(usb)
assert len(endpoints) == 2 and all(e['max_packet'] == 16 for e in endpoints)
report = {
    'source_sha256': {'QCPNP.c': hashlib.sha256(pnp_bytes).hexdigest(), 'QCWT.c': hashlib.sha256(write_bytes).hexdigest(), 'QCMAIN.h': hashlib.sha256((source / 'QCMAIN.h').read_bytes()).hexdigest()},
    'option': 'QCDeviceZLPEnabled', 'default': True,
    'value_semantics': {'absent_or_failed_read': True, 'dword_zero': False, 'positive_dword': True},
    'registry_scope': 'PLUGPLAY_REGKEY_DRIVER (device software key), populates driver-global gVendorConfig',
    'load_callback': 'QCPNP_EvtDeviceAdd', 'load_call_line': 91,
    'not_reread_by_ordinary_FileCreate': True,
    'preserve_toggle_option_read_in_FileCreate': True,
    'zlp_condition': condition,
    'based_on_requested_length_not_successful_completion': True,
    'function_lines': {'DeviceAdd': add_line, 'FileCreate': open_line, 'VendorRegistryProcess': registry_line, 'WriteRequestHandlerThread': worker_line},
    'historical_endpoint_reference': 'reference/rx52/usb-overlap-02.json',
    'historical_endpoint_max_packet': 16,
    'fresh_endpoint_query_performed': False,
    'native_payload_14_wire_bytes': 16,
    'later_trial_requirement': 'Keep ZLP default in primary reopen off/on trial. Later change ZLP separately; prove DeviceAdd/registry reread and actual presence/absence of zero-byte OUT. Do not assume ordinary reopen or a power-only restart applies it.',
    'source_changed': False, 'registry_changed': False, 'hardware_validated': False,
    'limits': 'Source loading/dispatch audit and historical descriptor evidence; no current option execution, USB data, successful-ZLP policy proof or repair.',
}
out.write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
