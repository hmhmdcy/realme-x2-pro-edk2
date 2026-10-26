from pathlib import Path
from hashlib import sha256
import json
import pefile
from capstone import Cs,CS_ARCH_X86,CS_MODE_64
from capstone.x86 import X86_OP_MEM,X86_REG_RIP

root=Path(__file__).resolve().parent
binary=Path('/mnt/e/eud-host/qud_cab/qcusbser.sys')
assert sha256(binary.read_bytes()).hexdigest()=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
pe=pefile.PE(str(binary))
engine=Cs(CS_ARCH_X86,CS_MODE_64);engine.detail=True
symbols=json.loads((root.parent/'rx50/qcusbser-symbols.json').read_text())
by_rva={s['rva']:s['name'] for s in symbols}
imports={d.address-pe.OPTIONAL_HEADER.ImageBase:d.name.decode() for e in pe.DIRECTORY_ENTRY_IMPORT for d in e.imports if d.name}
targets={0x18f14:'QCSER_VendorRegistryProcess',0x18cc0:'QCSER_PostVendorRegistryProcess',0x2f074:'QCSER_CreateLogs'}
callers=[];global_refs=[];strings=[];copy_window=[]
for r in pe.DIRECTORY_ENTRY_EXCEPTION:
    start,end=r.struct.BeginAddress,r.struct.EndAddress
    code=pe.get_data(start,end-start)
    instructions=list(engine.disasm(code,start))
    assert sum(i.size for i in instructions)==len(code)
    for ins in instructions:
        if by_rva.get(start)=='QCPTDO_CreateNewPTDO' and 0x1a810<=ins.address<0x1a860:
            copy_window.append(dict(instruction=f'{ins.address:08x}',bytes=ins.bytes.hex(),text=ins.mnemonic+' '+ins.op_str,function_code_sha256=sha256(code).hexdigest()))
        if ins.mnemonic=='call' and ins.op_str.startswith('0x') and int(ins.op_str,16) in targets:
            callers.append(dict(caller=by_rva.get(start),call=f'{ins.address:08x}',target=targets[int(ins.op_str,16)],code_sha256=sha256(code).hexdigest()))
        for op in ins.operands:
            if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_RIP: continue
            rva=ins.address+ins.size+op.mem.disp
            if 0x3a320<=rva<0x3a360:
                global_refs.append(dict(function=by_rva.get(start),instruction=f'{ins.address:08x}',target=f'{rva:08x}',text=ins.mnemonic+' '+ins.op_str,access=op.access))
            if start!=0x2f074: continue
            if ins.mnemonic=='call':
                strings.append(dict(instruction=f'{ins.address:08x}',import_name=imports.get(rva)))
            if ins.mnemonic=='lea':
                raw=pe.get_data(rva,256); a=raw.split(b'\0')[0]
                if a and all(32<=b<127 for b in a):
                    strings.append(dict(instruction=f'{ins.address:08x}',rva=f'{rva:08x}',ascii=a.decode()))
(root/'logging-code-refs.json').write_text(json.dumps(dict(callers=callers,global_config_references=global_refs,file_creation_refs=strings),indent=2)+'\n')
(root/'config-copy-window.json').write_text(json.dumps(copy_window,indent=2)+'\n')
print(json.dumps(dict(callers=callers,initial_config_refs=[r for r in global_refs if r['function']=='QCSER_VendorRegistryProcess' and int(r['instruction'],16)<0x18f98],logging_bit_refs=[r for r in global_refs if r['target']=='0003a331'],creation_strings=[r for r in strings if 'ascii' in r]),indent=2))

events=json.loads((root.parent/'rx56/old-etw-target-transfers.json').read_text())
incoming=[e for e in events if e['fields'].get('fid_PipeHandle')==['0xFFFFC00BB56C89F0']]
for e in incoming[:3]: print(json.dumps(e))
