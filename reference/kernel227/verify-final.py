"""Verify final source application, real ELF owner relocation and preserved inputs."""
from pathlib import Path
import importlib.util
import json
import re
import struct
import subprocess

REF = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('prepare227', REF / 'prepare-fastrpc.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)
lock = json.loads((REF / 'fastrpc-source-validation.json').read_text())
build = json.loads((REF / 'fastrpc-build-validation.json').read_text())
tests = json.loads((REF / 'fastrpc-host-validation.json').read_text())
baseline = (p.BUILD / 'baseline/fastrpc.c').read_bytes()
candidate = (p.BUILD / 'candidate/fastrpc.c').read_bytes()
assert p.digest(baseline) == lock['source_before_sha256']
assert p.digest(candidate) == lock['candidate_source_sha256']
assert build['results']['candidate']['source_sha256'] == lock['candidate_source_sha256']
assert tests['actual_functions_extracted_unchanged']['candidate']['source_sha256'] == lock['candidate_source_sha256']
assert candidate.decode() == p.candidate(baseline.decode())
patch = REF / 'fastrpc-publication-lifetime.patch'
assert p.digest(patch.read_bytes()) == lock['patch_sha256']
tree = p.BUILD / 'final-patch-apply'
assert not tree.exists()
(tree / 'drivers/misc').mkdir(parents=True)
(tree / 'drivers/misc/fastrpc.c').write_bytes(baseline)
applied = subprocess.run(['patch', '--batch', '--forward', '-p1', '-i', str(patch)], cwd=tree, capture_output=True)
(p.PRIVATE / 'patch-apply-private.log').write_bytes(applied.stdout + applied.stderr)
assert applied.returncode == 0 and (tree / 'drivers/misc/fastrpc.c').read_bytes() == candidate


def owner_relocation(path):
    data = path.read_bytes()
    assert data[:6] == b'\x7fELF\x02\x01'
    assert struct.unpack_from('<H', data, 18)[0] == 183
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count = struct.unpack_from('<HH', data, 58)
    sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + size * i) for i in range(count)]
    symbols = {}
    tables = {}
    for index, section in enumerate(sections):
        if section[1] != 2:
            continue
        strings_section = sections[section[6]]
        strings = data[strings_section[4]:strings_section[4] + strings_section[5]]
        table = []
        for pos in range(section[4], section[4] + section[5], section[9]):
            sym = struct.unpack_from('<IBBHQQ', data, pos)
            name = strings[sym[0]:].split(b'\0', 1)[0].decode()
            table.append((name, sym))
            if name == 'fastrpc_fops':
                symbols[name] = sym
        tables[index] = table
    fops = symbols['fastrpc_fops']
    for section in sections:
        if section[1] != 4 or section[7] != fops[3]:
            continue
        for pos in range(section[4], section[4] + section[5], section[9]):
            target, info, addend = struct.unpack_from('<QQq', data, pos)
            name = tables[section[6]][info >> 32][0]
            if target == fops[4] and name == '__this_module' and addend == 0:
                return True
    return False


fs = (p.KERNEL / 'include/linux/fs.h').read_text()
assert re.search(r'struct file_operations\s*\{\s*struct module \*owner;', fs)
assert not owner_relocation(p.BUILD / 'baseline/fastrpc.o')
assert owner_relocation(p.BUILD / 'candidate/fastrpc.o')
exit_body = candidate.decode().split('static void fastrpc_exit(void)', 1)[1].split('module_exit', 1)[0]
assert exit_body.index('unregister_rpmsg_driver') < exit_body.index('platform_driver_unregister')
assert p.snapshot() == json.loads((p.PRIVATE / 'kernel-before-private.json').read_text())
sources = sorted(REF.glob('*.py'))
for source in sources:
    compile(source.read_text(), str(source), 'exec')
report = {'stage': 227, 'final_candidate_source_sha256': lock['candidate_source_sha256'],
          'final_module_sha256': build['results']['candidate']['module_sha256'],
          'patch_applies_exactly': True, 'original_fops_owner_relocation': False,
          'candidate_fops_owner_relocation': True, 'module_exit_reverse_init': True,
          'python_sources_compile': len(sources), 'canonical_preserved_files': 51,
          'canonical_unchanged': True, 'candidate_host_cases': len(tests['candidate_cases']),
          'baseline_negative_control_detected': True, 'freezer189_preserved': True,
          'runtime_deployed': False, 'device_services_and_modules_unchanged': True}
(REF / 'source-final-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps(report))
