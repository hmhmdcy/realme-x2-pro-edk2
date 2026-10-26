from hashlib import sha256
import json
from pathlib import Path
import re
import runpy
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64

out = Path(__file__).resolve().parent
binary = Path('/mnt/e/eud-host/qud_cab/qcusbser.sys')
pdb = binary.with_suffix('.pdb')
installed = Path('/mnt/c/Windows/System32/drivers/qcusbser.sys')
assert sha256(binary.read_bytes()).hexdigest() == sha256(installed.read_bytes()).hexdigest() == 'ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
assert sha256(pdb.read_bytes()).hexdigest() == 'ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
pe = pefile.PE(str(binary))
symbols = json.loads((out.parent/'rx50/qcusbser-symbols.json').read_text())
names = {s['rva']: s['name'] for s in symbols}
engine = Cs(CS_ARCH_X86, CS_MODE_64)
refs = []
for entry in pe.DIRECTORY_ENTRY_EXCEPTION:
    start, end = entry.struct.BeginAddress, entry.struct.EndAddress
    code = pe.get_data(start, end-start)
    instructions = list(engine.disasm(code, start))
    assert sum(i.size for i in instructions) == len(code)
    for n, i in enumerate(instructions):
        match = re.search(r'\[rip ([+-]) (0x[0-9a-f]+)\]', i.op_str)
        if i.mnemonic == 'lea' and match:
            offset = int(match[2], 16) * (1 if match[1] == '+' else -1)
            if i.address+i.size+offset == 0x25408:
                refs.append(dict(caller=names.get(start), rva=f'{i.address:08x}',
                                 code_sha256=sha256(code).hexdigest(),
                                 instructions=[dict(rva=f'{x.address:08x}', bytes=x.bytes.hex(' '),
                                                    mnemonic=x.mnemonic, operands=x.op_str)
                                               for x in instructions[max(0,n-2):n+9]]))
(out/'callback-refs.json').write_text(json.dumps(refs, indent=2)+'\n')
print(json.dumps(refs, indent=2))
