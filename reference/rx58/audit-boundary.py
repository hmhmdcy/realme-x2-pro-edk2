"""Select exact driver branches. Reads PE/PDB only; never loads a driver."""
from hashlib import sha256
import json
from pathlib import Path
import runpy
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
import pefile

root = Path(__file__).resolve().parent
binary = Path('/mnt/e/eud-host/qud_cab/qcusbser.sys')
pdb = binary.with_suffix('.pdb')
installed = Path('/mnt/c/Windows/System32/drivers/qcusbser.sys')
assert sha256(installed.read_bytes()).hexdigest() == sha256(binary.read_bytes()).hexdigest() == 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
identity = json.loads((root/'exact-driver/qcusbser-identity.json').read_text())
assert identity['identity_matches'] and identity['section_headers_match']
assert identity['pdb_sha256'] == sha256(pdb.read_bytes()).hexdigest() == 'ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
pe = pefile.PE(str(binary))
engine = Cs(CS_ARCH_X86, CS_MODE_64)
ranges = [
    ('L2-success-and-error-log', 'QCMRD_L2MultiReadThread', 0xef6c, 0xf004),
    ('L2-status-and-length-ring', 'QCMRD_L2MultiReadThread', 0xf07e, 0xf128),
    ('L1-completion-gates', 'QCMRD_L1MultiReadThread', 0xd216, 0xd265),
    ('L1-ring-to-callback', 'QCMRD_L1MultiReadThread', 0xd67f, 0xd73a),
    ('IOB-read-callback-binding', 'StartTheReadGoing', 0x2845c, 0x28479),
    ('read-status-vPut-gate', 'ReadIrpCompletion', 0x25424, 0x25490),
]
rows = []
for label, name, begin, end in ranges:
    fn, = [f for f in identity['functions'] if f['name'] == name]
    fn_begin, fn_end = int(fn['start_rva'], 16), int(fn['end_rva'], 16)
    assert fn_begin <= begin < end <= fn_end
    code = pe.get_data(fn_begin, fn_end-fn_begin)
    assert sha256(code).hexdigest() == fn['code_sha256']
    instructions = list(engine.disasm(code, fn_begin))
    selected = [i for i in instructions if begin <= i.address < end]
    assert selected[0].address == begin and selected[-1].address+selected[-1].size == end
    original = (root/'exact-driver'/fn['disassembly']).read_text().splitlines()
    selected_lines = [line.rstrip() for line in original if begin <= int(line[:8], 16) < end]
    assert len(selected_lines) == len(selected)
    filename = label+'.asm.txt'
    (root/filename).write_text('\n'.join(selected_lines)+'\n')
    rows.append(dict(label=label, name=name, begin=f'{begin:08x}', end=f'{end:08x}',
                     bytes=sum(i.size for i in selected),
                     excerpt_code_sha256=sha256(b''.join(i.bytes for i in selected)).hexdigest(),
                     function_code_sha256=fn['code_sha256'], filename=filename))
report = dict(binary_sha256=identity['binary_sha256'], installed_binary_matches=True,
              pdb_sha256=identity['pdb_sha256'], guid=identity['guid'], age=identity['age'],
              functions=identity['functions'], excerpts=rows,
              facts=[
                  'L2 records successful read payload only when IoStatus.Status == 0; nonzero logs type 3 with four status bytes, without payload or transfer length.',
                  'L2 retains status and URB TransferBufferLength in ring fields +0x10/+0x20 even for nonzero status; this is not an L2 blanket discard.',
                  'The L1 normal completion path copies status, length and buffer to IOB +0x58/+0x48/+0x20 and invokes IOB +0x60. Other cancellation/state gates also exist.',
                  'StartTheReadGoing binds IOB +0x60 to ReadIrpCompletion at RVA 0x25408.',
                  'ReadIrpCompletion reaches AdjustPaddingBytes and vPutToReadBuffer only with IOB status == 0 and positive length. Nonzero status skips this payload insertion.'
              ],
              limits=[
                  'No fault-time nonzero-status partial transfer is measured; this branch is a candidate, not the root cause.',
                  'A positive URB length on failure is not by itself proof of valid returned bytes; it must be interpreted with status, actual transfer evidence and API rules.',
                  'Missing data in this logger does not distinguish physical/EUD loss from a failed completion whose payload was not logged.',
                  'Static code does not measure live flag state or all indirect/dynamically altered paths.'
              ])
(root/'driver-boundary-summary.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(dict(excerpts=len(rows), instructions=sum(1 for row in rows for _ in (root/row['filename']).read_text().splitlines()), facts=report['facts']), indent=2))
