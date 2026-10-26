from pathlib import Path
import hashlib, json, struct, zipfile

root = Path('/mnt/e/edk2-samurai-out/rx62')
package = root / 'package-windows11'
binary = (package / 'qcwdfserial.sys').read_bytes()
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha(binary) == '3cceeafcb3c5656e87de130d938f748cdc3875e826c63f9826440b56674b4a2a'
pe = struct.unpack_from('<I', binary, 0x3c)[0]
assert binary[:2] == b'MZ' and binary[pe:pe+4] == b'PE\0\0'
machine, count, timestamp, _, _, optional_size, characteristics = struct.unpack_from('<HHIIIHH', binary, pe + 4)
optional = pe + 24
magic = struct.unpack_from('<H', binary, optional)[0]
subsystem, dll_flags = struct.unpack_from('<HH', binary, optional + 68)
alignment = struct.unpack_from('<I', binary, optional + 32)[0]
certificate_offset, certificate_size = struct.unpack_from('<II', binary, optional + 112 + 4*8)
assert machine == 0x8664 and magic == 0x20b and subsystem == 1
assert alignment == 4096 and dll_flags & 0x100 and not certificate_size
sections = []
for i in range(count):
    at = optional + optional_size + i*40
    name = binary[at:at+8].split(b'\0',1)[0].decode('ascii')
    virtual_size, virtual_address, raw_size, raw_offset = struct.unpack_from('<IIII', binary, at+8)
    flags = struct.unpack_from('<I', binary, at+36)[0]
    executable, writable = bool(flags & 0x20000000), bool(flags & 0x80000000)
    assert not (executable and writable), name
    assert raw_offset + raw_size <= len(binary)
    sections.append({'name': name, 'virtual_address': virtual_address, 'raw_bytes': raw_size,
                     'executable': executable, 'writable': writable})
new_key = 'QCEudPreserveToggleOnOpen\0'.encode('utf-16le')
assert new_key in binary
inf = (package / 'qceudexp.inf').read_text()
assert inf.count('USB\\VID_05C6&PID_9505') == 1
assert 'KmdfLibraryVersion=1.15' in inf and 'NTamd64.10.0...26100' in inf
source = Path('/mnt/e/edk2-samurai-out/rx61/source-pinned/qcom-usb-kernel-drivers-14b6fe1ee69cdd9182502629da9192156b9d206a')
modules = {}
with zipfile.ZipFile('/mnt/e/edk2-samurai-out/rx61/qcom-14b6fe1-source.zip') as z:
    prefix = z.namelist()[0]
    for p in sorted((source / 'src/windows/wdfserial').glob('*.c')):
        old = z.read(prefix + 'src/windows/wdfserial/' + p.name)
        data = p.read_bytes()
        assert (data != old) == (p.name == 'QCPNP.c')
        modules[p.name] = sha(data)
assert len(modules) == 9 and modules['QCPNP.c'] == '7cf3f3db7878d4a1a037da075e4dfda6985851b7805a42434cf3ae2202c014fd'
report = {'sys_sha256': sha(binary), 'sys_bytes': len(binary), 'machine': 'AMD64',
          'subsystem': 'Native', 'section_alignment': alignment, 'nx_compatible': bool(dll_flags & 0x100),
          'dynamic_base': bool(dll_flags & 0x40), 'guard_cf': bool(dll_flags & 0x4000),
          'no_executable_writable_sections': True, 'sections': sections,
          'new_opt_in_key_present_in_linked_binary': True, 'unsigned_certificate_table_size': certificate_size,
          'source_module_sha256': modules, 'runtime_hvci_compatibility_proved': False,
          'hardware_validated': False,
          'limits': 'PE/source provenance checks only; no Windows kernel loading, Driver Verifier or USB stability test.'}
(root / 'binary-audit.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k: report[k] for k in ['sys_sha256','sys_bytes','machine','subsystem','nx_compatible','no_executable_writable_sections','new_opt_in_key_present_in_linked_binary','hardware_validated']}))
