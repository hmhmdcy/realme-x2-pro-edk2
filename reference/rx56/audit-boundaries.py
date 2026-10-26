from pathlib import Path
from hashlib import sha256
import json
from collections import Counter
import xml.etree.ElementTree as ET
import pefile
from capstone import Cs, CS_ARCH_X86, CS_MODE_64
from capstone.x86 import X86_OP_MEM, X86_REG_RIP

root=Path(__file__).resolve().parent
binary=Path('/mnt/e/eud-host/qud_cab/qcusbser.sys')
assert sha256(binary.read_bytes()).hexdigest()=='ad2ace071d2362d8712820f62570757e1af266a054d2c3d3a6964a41e7cc6151'
pe=pefile.PE(str(binary))
engine=Cs(CS_ARCH_X86,CS_MODE_64); engine.detail=True
identity=json.loads((root/'front-audit/qcusbser-identity.json').read_text())
refs=[]
for f in identity['functions']:
    if 'RegistryProcess' not in f['name']: continue
    start=int(f['start_rva'],16); end=int(f['end_rva'],16)
    for ins in engine.disasm(pe.get_data(start,end-start),start):
        if ins.mnemonic!='lea': continue
        for op in ins.operands:
            if op.type!=X86_OP_MEM or op.mem.base!=X86_REG_RIP: continue
            rva=ins.address+ins.size+op.mem.disp
            raw=pe.get_data(rva,256)
            units=[]
            for n in range(0,len(raw)-1,2):
                unit=int.from_bytes(raw[n:n+2],'little')
                if unit==0: break
                if not 32<=unit<127: units=[]; break
                units.append(chr(unit))
            if len(units)>=4:
                refs.append(dict(function=f['name'],instruction=f'{ins.address:08x}',rva=f'{rva:08x}',text=''.join(units)))
(root/'registry-key-refs.json').write_text(json.dumps(refs,indent=2)+'\n')

src=root.parent/'rx46/etw-r46g-capture.all-local-lr.xml'
ns={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
target=[]
for ev in ET.parse(src).getroot().findall('e:Event',ns):
    sys=ev.find('e:System',ns)
    fields={}
    for node in ev.findall('.//e:Data',ns):
        name=node.get('Name')
        if name: fields.setdefault(name,[]).append((node.text or '').strip())
    if fields.get('fid_UsbDevice')!=['0x3FF44207E648']: continue
    if sys.find('e:Provider',ns).get('Name')!='Microsoft-Windows-USB-UCX': continue
    eid=sys.findtext('e:EventID',namespaces=ns)
    if eid not in ('26','27'): continue
    target.append(dict(id=eid,version=sys.findtext('e:Version',namespaces=ns),
                       stamp=sys.find('e:TimeCreated',ns).get('SystemTime'),fields=fields))
incoming=[r for r in target if r['id']=='27' and r['fields'].get('fid_PipeHandle')==['0xFFFFC00BB56C89F0']]
lengths=Counter(r['fields'].get('fid_URB_TransferBufferLength',['?'])[0] for r in incoming)
result=dict(source_sha256=sha256(src.read_bytes()).hexdigest(),
            target_transfer_events=len(target),in_completions=len(incoming),
            in_length_histogram=dict(lengths),
            in_completed_bytes=sum(int(k,0)*v for k,v in lengths.items()),
            raw_bytes={name:len((root.parent/'rx46'/name).read_bytes()) for name in ['etw-r46g-capture.native.raw','etw-r46g-capture.metrics.raw']},
            payload_captured=False,physical_data_pid_captured=False,
            note='Old RX46 capture; aggregate URB lengths do not locate an RX55 payload gap.')
(root/'old-etw-target-transfers.json').write_text(json.dumps(target,indent=2)+'\n')
(root/'old-etw-in-summary.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(registry_refs=refs,old_etw=result),indent=2))
