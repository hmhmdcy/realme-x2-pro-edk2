from pathlib import Path
from collections import Counter
import json

root=Path(__file__).resolve().parent
events=json.loads((root.parent/'rx56/old-etw-target-transfers.json').read_text())
pending={};timeline=[];unmatched=[];peak=0;requested=Counter()
for event in events:
    fields=event['fields']
    if fields.get('fid_PipeHandle')!=['0xFFFFC00BB56C89F0']: continue
    key=(fields['fid_IRP_Ptr'][0],fields['fid_URB_Ptr'][0])
    if event['id']=='26':
        assert key not in pending,(event['stamp'],key)
        pending[key]=event['stamp']
        requested[fields['fid_URB_TransferBufferLength'][0]]+=1
    elif event['id']=='27':
        if key not in pending: unmatched.append(event)
        else: del pending[key]
    peak=max(peak,len(pending))
    timeline.append(dict(stamp=event['stamp'],event_id=event['id'],irp=key[0],urb=key[1],outstanding=len(pending)))
result=dict(peak_concurrent_in=peak,in_dispatch_lengths=dict(requested),unmatched_completions=unmatched,
            pending_at_end=pending if not pending else [{ 'irp':k[0],'urb':k[1],'stamp':v} for k,v in pending.items()],
            timeline=timeline,note='RX46 historical runtime evidence, not a current live worker read; no physical PID/ACK.')
(root/'etw-outstanding.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='timeline'},indent=2))
