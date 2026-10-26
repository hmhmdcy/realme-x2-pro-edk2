from pathlib import Path
import json,re
P=Path('/mnt/e/edk2-samurai-out/kernel241')
lines=(P/'libloc_api_v02.so.disasm-private.txt').read_text().splitlines()
items=[]
for i,line in enumerate(lines):
    if re.search(r'\bbl\b.*<(?:LocApiV02::locSyncSendReq|LocApiV02::locClientSendReq|locClientSendReq)',line):
        context=lines[max(0,i-25):i+1]
        candidates=[]
        for prev in reversed(context[:-1]):
            if re.search(r'\bbl\b',prev):break
            m=re.search(r'mov\s+w1, #0x([0-9a-f]+)',prev)
            if m:candidates.append(int(m[1],16))
        item=dict(call_address=line.split(':')[0].strip(),message_id=candidates[0] if candidates else None,
                  context='\n'.join(context))
        items.append(item)
(P/'qmi-calls-private.json').write_text(json.dumps(items,indent=2)+'\n')
for item in items:
    if item['message_id'] in (0xba,0xd0,0x88,0x22,0xa9,0x6e,0x4a):
        print('\n'+item['context'])
print('direct QMI send sites',len(items),'resolved immediate IDs',sum(x['message_id'] is not None for x in items))
