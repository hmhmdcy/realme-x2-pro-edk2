from hashlib import sha256
import json
from pathlib import Path
import runpy

import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64

root=Path(__file__).resolve().parent
binary=Path('/mnt/e/eud-host/qud_cab/qcusbser.sys')
pdb=Path('/mnt/e/eud-host/qud_cab/qcusbser.pdb')
assert sha256(binary.read_bytes()).hexdigest()=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
assert sha256(pdb.read_bytes()).hexdigest()=='ee203464fc2ab419eaa66c90e345e24eba3fa0e103c0fe11f91e428897ef9155'
inspect=runpy.run_path(str(root.parent/'rx50/inspect-qcusbser.py'))['inspect']
pe=pefile.PE(str(binary))
symbols=json.loads((root.parent/'rx50/qcusbser-symbols.json').read_text())
names={s['rva']:s['name'] for s in symbols}
targets={168528:'vPutToReadBuffer',189068:'QCUSB_ResetInput',190320:'QCUSB_ResetOutput',194312:'QCSER_LogData'}
engine=Cs(CS_ARCH_X86,CS_MODE_64)
calls=[]
for r in pe.DIRECTORY_ENTRY_EXCEPTION:
    start,end=r.struct.BeginAddress,r.struct.EndAddress
    code=pe.get_data(start,end-start)
    instructions=list(engine.disasm(code,start))
    assert sum(i.size for i in instructions)==len(code)
    for i in instructions:
        if i.mnemonic=='call' and i.op_str.startswith('0x'):
            target=int(i.op_str,16)
            if target in targets:
                calls.append(dict(caller=names.get(start),start=f'{start:08x}',end=f'{end:08x}',
                                  call=f'{i.address:08x}',target=targets[target],code_sha256=sha256(code).hexdigest()))
(root/'exact-callers.json').write_text(json.dumps(calls,indent=2)+'\n',encoding='utf-8')
types=json.loads((root.parent/'rx50/qcusbser-types.json').read_text())
selected=[]
for t in types:
    if 'DEVICE_EXTENSION' not in t['name']: continue
    members=[m for m in t['members'] if m['offset'] in (0x358,0x470,0x11c0,0x11c2,0xdb8,0x2d2,0x2d3,0x2d7)]
    selected.append(dict(name=t['name'],size=t['size'],type=t['type'],members=members))
(root/'boundary-types.json').write_text(json.dumps(selected,indent=2)+'\n',encoding='utf-8')
selected_names=sorted({c['caller'] for c in calls if c['target']=='vPutToReadBuffer' and c['caller']})
report=inspect(binary,pdb,selected_names+['QCSER_LogData','QCSER_VendorRegistryProcess','QCSER_PostVendorRegistryProcess'],root/'front-audit')
print(json.dumps(dict(calls=calls,types=selected,functions=[dict(name=f['name'],size=f['size']) for f in report['functions']]),indent=2))
