"""Offline analysis of previously captured GNSS ELF files. Never execute them."""
from pathlib import Path
import hashlib
import json
import re
import subprocess

R = Path(__file__).resolve().parent
P = Path('/mnt/e/edk2-samurai-out/kernel241')
P.mkdir(mode=0o700, exist_ok=True)
V = Path('/mnt/e/edk2-samurai-out/kernel238/vendor-source-private')
F = Path('/mnt/e/edk2-samurai-out/kernel238/vendor-followup-source-private')
results = {}
for source in (V, F):
    manifest = json.loads((source / 'files-manifest-private.json').read_text())
    for name, item in manifest.items():
        path = source / 'payload' / name
        if not item['elf'] or '/lib/' in name or not re.search(
                r'lib(gnss|loc_api_v02|loc_core|gps\.utils|lbs_core|qmi_cci)\.so$', name):
            continue
        data = path.read_bytes()
        assert len(data) == item['bytes']
        assert hashlib.sha256(data).hexdigest() == item['sha256']
        key = path.name
        symbols_raw = subprocess.check_output(['readelf', '--dyn-syms', '--wide', str(path)], text=True)
        symbols = subprocess.check_output(['c++filt'], input=symbols_raw, text=True)
        (P / (key + '.symbols-private.txt')).write_text(symbols)
        asm = subprocess.check_output(['aarch64-linux-gnu-objdump', '-d', '-C', str(path)], text=True)
        (P / (key + '.disasm-private.txt')).write_text(asm)
        results[key] = dict(bytes=len(data), sha256=item['sha256'], source_manifest_verified=True,
                            disassembly_bytes=len(asm), function_symbols=symbols.count(' FUNC '))
        if key in ('libgnss.so', 'libloc_api_v02.so'):
            selected = []
            for line in symbols.splitlines():
                m = re.match(r'\s*\d+:\s*([0-9a-f]+)\s+(\d+)\s+FUNC\s+\S+\s+\S+\s+(\S+)\s+(.*)', line)
                if m and m[3] != 'UND' and re.search(
                        r'::(open\(|setConfig\(|handleEngineUpEvent\(|registerMasterClient\(|'
                        r'startTimeBasedTracking\(|startFix\(|setGnssBiases\(|setSvMeasurementConstellation\(|'
                        r'updateSystemPowerState\(|readConfig\(|setOperationMode\(|gnssUpdateConfig\()', m[4]):
                    start, size = int(m[1], 16), int(m[2])
                    code = subprocess.check_output(['aarch64-linux-gnu-objdump', '-d', '-C',
                        '--start-address=' + str(start), '--stop-address=' + str(start + size), str(path)], text=True)
                    selected.append(dict(name=m[4], address=hex(start), size=size, disassembly=code))
            (P / (key + '.selected-private.json')).write_text(json.dumps(selected, indent=2) + '\n')
report = dict(stage=241, source='previously exported actual vendor files',
              offline_only=True, vendor_code_executed=False, files=results)
(R / 'hal-elf-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
