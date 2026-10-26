"""Recover only interoperability facts from the privately retained factory ELF."""
from pathlib import Path
import hashlib
import json
import lzma
import re
import struct
import subprocess
import host

ROOT = Path(__file__).resolve().parent
binary = host.PRIVATE / 'camera.qcom.so-private'
data = binary.read_bytes()
pin = json.loads((ROOT / 'oem-hal-source-validation.json').read_text())
assert hashlib.sha256(data).hexdigest() == pin['sha256']
assert data[:6] == b'\x7fELF\x02\x01'
offset = struct.unpack_from('<Q', data, 40)[0]
size, count, index = struct.unpack_from('<HHH', data, 58)
sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
names = data[sections[index][4]:sections[index][4] + sections[index][5]]
section = next(s for s in sections if names[s[0]:].split(b'\0', 1)[0] == b'.gnu_debugdata')
debug = lzma.decompress(data[section[4]:section[4] + section[5]])
debug_path = host.PRIVATE / 'hal-debugdata-private.elf'
debug_path.write_bytes(debug)
symbols = subprocess.check_output(['aarch64-linux-gnu-nm', '-S', '-n', '-C', str(debug_path)], text=True)
(host.PRIVATE / 'hal-debug-symbols-with-size-private.txt').write_text(symbols)
targets = ['IFECAMIF::Execute', 'IFEBLS12::Execute', 'IFEDemux13::Execute',
           'IFEWB12::Execute', 'IFEDemosaic36::Execute', 'IFEDemosaic37::Execute',
           'IFECST12::Execute', 'IFECC12::Execute', 'IFEGamma16::Execute',
           'IFEMNDS16::Execute', 'IFECrop10::Execute', 'IFERoundClamp11::Execute',
           'IFENode::ProgramIQConfig', 'IFENode::ProgramIQEnable',
           'IFENode::ProgramIQModuleEnableConfig', 'IFENode::UpdateIFECapabilityBasedOnCameraPlatform']
records = []
for name in targets:
    matches = [line for line in symbols.splitlines() if name + '(' in line]
    assert len(matches) == 1, (name, matches)
    fields = matches[0].split(maxsplit=3)
    start, length = int(fields[0], 16), int(fields[1], 16)
    assert fields[2] in ['t', 'T'] and length < 100000
    dis = subprocess.check_output(['aarch64-linux-gnu-objdump', '-d', '--start-address=' + hex(start),
                                  '--stop-address=' + hex(start + length), str(binary)], text=True)
    filename = name.replace('::', '-') + '-disassembly-private.txt'
    (host.PRIVATE / filename).write_text(dis)
    instructions = dis.splitlines()
    calls = []
    for i, line in enumerate(instructions):
        if re.search(r'\b(?:bl|b)\s+52cb10\b', line):
            # These are evidence windows, not a control-flow analysis. In
            # particular a value loaded from a table is not a literal address.
            window = instructions[max(0, i - 16):i + 1]
            literal = {}
            for previous in window[:-1]:
                match = re.search(r'\bmov\s+w([12]), #0x([0-9a-f]+)', previous)
                if match:
                    literal[match[1]] = int(match[2], 16)
            calls.append(dict(callsite=line.strip().split(':', 1)[0],
                              preceding_literal_w1=literal.get('1'), preceding_literal_w2=literal.get('2')))
            print(name + '\n' + '\n'.join(window[-10:]))
    records.append(dict(symbol=name, address=hex(start), bytes=length,
                        private_disassembly_sha256=hashlib.sha256(dis.encode()).hexdigest(),
                        write_range_call_windows=calls))
report = dict(stage=281, source_sha256=pin['sha256'], debugdata_sha256=hashlib.sha256(debug).hexdigest(),
              debugdata_bytes=len(debug), functions=records, no_oem_execution=True,
              literal_windows_require_manual_control_flow_validation=True,
              no_complete_tuning_or_hardware_validation_claimed=True)
(ROOT / 'hal-static-analysis-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print('Private disassembly retained; source binary and debug ELF are not published.')
