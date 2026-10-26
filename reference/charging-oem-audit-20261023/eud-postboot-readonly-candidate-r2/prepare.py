"""Offline composition from pinned read-only helpers; no worker imports."""
from pathlib import Path
import ast, hashlib, json, textwrap
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
base = REF / 'charging-oem-audit-20261023/normal-restart-candidate/r7-postboot.py'
ram = REF / 'charging-management-20261023/read-eud-ram-r8.py'
guard = REF / 'charging-session-20261023/eud-boot-activation-candidate/guard-fragment.py'
assert sha(base) == 'df94745cc48e314b3e886d32a936dbdc7a75351dc7af049c08986c9e76f93bfa'
assert sha(ram) == 'c6f42e51a9f582373004b75074d2e99913e002c4ca5c0291ac1f0f8e35980443'
assert sha(guard) == '80c25f129fc6319aff189368a527e0a912868ba7d0d1823054d75188502a18a6'
def functions(path, names):
    source = path.read_text(); rows = source.splitlines(True); result = []
    for node in ast.parse(source).body:
        if isinstance(node, ast.FunctionDef) and node.name in names:
            result.append(''.join(rows[node.lineno-1:node.end_lineno]) + '\n\n')
    assert len(result) == len(names)
    return ''.join(result)
names = ['attempt','read','command','file_fact','elf_note','module_fact','parse_kv','active','check_file']
helpers = functions(base, names)
constants = []
for node in ast.parse(guard.read_text()).body:
    if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id in {
            'CANDIDATE_BOOT','ROLLBACK_BOOT','IMAGE363','LOGDUMP365','CAMERA481','R8_MANIFEST','R8_NOTES','SENSOR468_NOTE'}:
        constants.append(ast.get_source_segment(guard.read_text(), node))
assert len(constants) == 8
read_code = next(ast.literal_eval(node.value) for node in ast.parse(ram.read_text()).body
                 if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name) and node.targets[0].id == 'READ_CODE')
marker = "print(json.dumps({'phase':'private_raw'"
assert read_code.count(marker) == 1
capture = read_code.split(marker)[0]
ring = 'def read_ring():\n' + textwrap.indent(capture.strip() + '\n', ' ') + ''' return {'raw_b64':base64.b64encode(raw).decode(), 'header_before':list(fields),
         'header_after':list(struct.unpack('<8I',after)), 'header_stable':before==raw[:32]==after,
         'reserved_cover':[x[0] for x in cover], 'physical_start':start, 'mapped_bytes':total,
         'explicit_memory_bytes_read':total+64, 'hardware_writes':0}

'''
header = '''"""One-shot postboot reads only. Default --check-local never collects.
No SSH implementation, guard adoption, CSR access or automatic recovery.
"""
from pathlib import Path
import argparse,base64,fcntl,hashlib,json,mmap,os,re,stat,struct,subprocess,sys,time
sha=lambda raw:hashlib.sha256(raw).hexdigest()
'''
device = header + '\n'.join(constants) + '\n\n' + helpers + ring + (HERE/'device-body.py').read_text()
ast.parse(device)
(HERE/'device.py').write_text(device, newline='\n')
result = dict(offline_only=True, workers_executed=False,
              source_files={str(p.relative_to(REF)):sha(p) for p in [base, ram, guard]},
              reused_functions=names, ring_capture_sha256=hashlib.sha256(capture.encode()).hexdigest(),
              device_sha256=sha(HERE/'device.py'))
(HERE/'source-result.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result, indent=2))
