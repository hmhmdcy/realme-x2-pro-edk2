"""Pair target-only UCX events, compare observed lengths to raw-driver records."""
from pathlib import Path
from collections import Counter
import json, xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parent
for prefix in ('joint-first-status','parity'):
    p=ROOT/(prefix+'-etw-summary.json')
    data=json.loads(p.read_text());active={};pairs=[]
    for r in data['target_transfers']:
        f=r['fields'];key=(f['fid_URB_Ptr'],f['fid_IRP_Ptr'],f['fid_PipeHandle'])
        if r['id']==26:
            assert key not in active;active[key]=r
        else:
            assert key in active
            a=active.pop(key);af=a['fields']
            assert int(f['fid_URB_TransferBufferLength'],0)<=int(af['fid_URB_TransferBufferLength'],0)
            assert a['timestamp']<=r['timestamp']
            pairs.append(dict(dispatch=a['timestamp'],completion=r['timestamp'],pipe=f['fid_PipeHandle'],requested=int(af['fid_URB_TransferBufferLength'],0),completed=int(f['fid_URB_TransferBufferLength'],0),ntstatus=f['fid_IRP_NtStatus'],usbd_status=f['fid_URB_Hdr_Status']))
    assert not active
    good=[r for r in pairs if r['pipe']==data['pipes']['0x81'] and r['ntstatus']==r['usbd_status']=='0x0']
    failed=[r for r in pairs if r['pipe']==data['pipes']['0x81'] and r not in good]
    assert all(r['completed']==0 and (r['ntstatus'],r['usbd_status'])==('0xC0000120','0xC0010000') for r in failed)
    source=ROOT.parent/'rx58' if prefix=='joint-first-status' else ROOT
    logdir=source/('driver-logs-first-status-01' if prefix=='joint-first-status' else 'driver-logs-parity-01')
    lengths=[]
    for f in sorted(logdir.glob('*Rx*.log')):
        d=json.loads((ROOT/(f.name+'.json')).read_text());lengths.extend(x['length'] for x in d['records'] if x['type'] in (0,5))
    assert lengths==[r['completed'] for r in good]
    # Open/reset control transfers: first SETUP Data element is the request.
    controls=[]
    ns={'e':'http://schemas.microsoft.com/win/2004/08/events/event'}
    for ev in ET.parse(ROOT/(prefix+'-etw-eud.xml')).getroot().findall('e:Event',ns):
        eid=int(ev.findtext('e:System/e:EventID',namespaces=ns))
        if eid not in (23,24): continue
        fs={n.get('Name'):(n.text or '').strip() for n in ev.findall('.//e:Data',ns) if n.get('Name')}
        controls.append(dict(id=eid,timestamp=ev.find('e:System/e:TimeCreated',ns).get('SystemTime'),fields=fs))
    summary=dict(source_etl_sha256=data['etl_sha256'],pair_count=len(pairs),all_dispatches_paired=True,successful_in_length_order_matches_driver=True,successful_in_count=len(good),successful_in_bytes=sum(lengths),failed_in_count=len(failed),failed_positive_in=0,failed_in_are_zero_length_close_cancels=True,failed_in=failed,out_zero_statuses=dict(Counter(r['ntstatus']+':'+r['usbd_status'] for r in pairs if r['pipe']==data['pipes']['0x2'] and not r['completed'])),control_events=controls,limits=['ETW reports software transfer headers, not physical DATA0/1 or USB ACKs.','First-status IN loss has no positive-length failed completion in this trace. This excludes that measured completion gate as an explanation for this particular gap.','Zero-length OUT retries after full 16-byte writes affect OUT parity accounting; count short startup requests separately.'])
    (ROOT/(prefix+'-etw-boundaries.json')).write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:v for k,v in summary.items() if k not in ('failed_in','control_events')},indent=2))
