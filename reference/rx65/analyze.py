"""Offline byte-boundary audit; never fills or edits received evidence."""
from pathlib import Path
from collections import Counter
from hashlib import sha256
import base64,gzip,json,re,struct,zlib,argparse

def capture(root,name):
    get=lambda ext:(root/(name+ext)).read_bytes() if (root/(name+ext)).exists() else gzip.decompress((root/(name+ext+'.gz')).read_bytes())
    raw=get('.raw');frames=[];pos=0
    while pos<len(raw):
        assert raw[pos]==0x90 and 1<=raw[pos+1]<=4
        stop=pos+2+raw[pos+1];assert stop<=len(raw)
        frames.append(raw[pos:stop]);pos=stop
    payload=b''.join(f[2:] for f in frames)
    assert get('.txt').decode('utf-8-sig').replace('\r','')==payload.decode().replace('\r','')
    events=[json.loads(s) for s in get('.events.jsonl').decode().splitlines()]
    meta=json.loads(get('.json'))
    closed=events[-1];assert closed['event']=='closed' and not closed['errors'] and not closed['worker_alive'] and closed['sink_drained']
    assert closed['frames']==len(frames) and closed['io_bytes']==len(raw) and not closed['stray'] and not closed['pending']
    reads=[bytes.fromhex(e['hex']) for e in events if e['event']=='in']
    assert b''.join(reads)==raw
    writes=[e for e in events if e['event']=='out_submit'];receipts=[e for e in events if e['event']=='receipt']
    assert all(e['attempt']==1 and e['length'] in (1,*range(3,15)) for e in writes)
    assert [(e['length'],e['payload_hex'],e['sync']) for e in writes]==[(e['length'],e['payload_hex'],e['sync']) for e in receipts]
    target=(meta['bus'],meta['address']);pending={};ins=[];outs=[];done=[];controls=[];statuses=Counter();zero_out=0;partial=[];requeues=[];last_c=None
    for line in get('.usbmon').decode().splitlines():
        f=line.split();a=f[3].split(':');assert tuple(map(int,a[1:3]))==target
        if a[0] in ('Ci','Co'):controls.append(line);continue
        n=int(f[5]);status=int(f[4]);data=bytes.fromhex(''.join(f[7:])) if len(f)>6 and f[6]=='=' else b''
        if a[0]=='Bi' and f[2]=='S' and last_c is not None:requeues.append(int(f[1])-last_c)
        if a[0]=='Bi' and f[2]=='C':
            last_c=int(f[1])
            statuses[str(status)]+=1
            if n:
                assert len(data)==n<=16
                if status:partial.append(dict(raw_frame=len(ins),status=status,length=n,wire=data.hex()))
                ins.append(data)
        if a[0]=='Bo':
            if f[2]=='S':
                assert len(data)==n<=16 and f[0] not in pending
                pending[f[0]]=data;outs.append(data);zero_out+=n==0
            if f[2]=='C':
                sent=pending.pop(f[0]);assert status==0 and n==len(sent);done.append(n)
    assert not pending and not controls and ins==reads==frames
    assert outs==[bytes.fromhex(e['hex']) for e in writes]
    assert done==[len(o) for o in outs]==[e['length'] for e in events if e['event']=='out_complete']
    result=dict(name=name,raw_bytes=len(raw),raw_sha256=sha256(raw).hexdigest(),frames=len(frames),payload_bytes=len(payload),
        in_statuses=dict(statuses),all_positive_in_equals_raw=True,out_submissions=len(outs),out_complete=True,out_zero_length=zero_out,
        no_capture_control_transfers=True,all_once_only_receipts=True,positive_cancelled_in=partial,
        max_requeue_gap_us=max(requeues),closed=closed)
    return result,payload,frames,events

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--out',type=Path);a=p.parse_args()
    results=[];captures={}
    for name in ('wsl-full','wsl-journal-ready','wsl-compressed'):
        r,payload,frames,events=capture(a.root,name);results.append(r);captures[name]=(payload,frames,events)
    payload,frames,events=captures['wsl-full']
    marker,=[e for e in events if e['event']=='overlap_marker'];end,=[e for e in events if e['event']=='overlap_end']
    probe,=[e for e in events if e['event']=='out_submit' and e['payload_hex']=='52 36 35 48 3d 31 32 33 34 35 36 37 38 0a']
    receipt,=[e for e in events if e['event']=='receipt' and e['payload_hex']==probe['payload_hex']]
    assert marker['ms']<probe['ms']<end['ms']<receipt['ms']
    assert re.search(rb'len=14 data=52 36 35 48 3d 31 32 33 34 35 36 37 38 0a s1_after=06060606 via=console',payload)
    body,=re.finditer(rb'(?m)^\[\s*\d+\.\d+\]\s*R65LOCK:(0+):R65END\n',payload)
    assert len(body[1])==990 and b'\nR65H=<12345678>\r\n' in payload
    results[0].update(console_zero_digits=990,probe_payload_bytes=14,probe_wire_bytes=16,probe_submissions=1,probe_via='console',
        marker_ms=marker['ms'],probe_ms=probe['ms'],end_ms=end['ms'],receipt_ms=receipt['ms'],receipt_latency_ms=round(receipt['ms']-probe['ms'],3),
        shell_variable_verified=True,status_lines=[s.decode() for s in re.findall(rb'(?m)^polls=[^\r\n]*',payload)])
    export=re.search(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',captures['wsl-journal-ready'][0])[0]
    bad=base64.b64decode(re.sub(rb'\s+',b'',export),validate=True);check=bytearray(bad);check[40:44]=bytes(4)
    results[1].update(base64_chars=len(re.sub(rb'\s+',b'',export)),decoded_bytes=len(bad),journal_crc_valid=zlib.crc32(check)==struct.unpack_from('<I',bad,40)[0])
    assert len(bad)==3117 and not results[1]['journal_crc_valid']
    export=re.search(rb'(?m)^H4sI[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',captures['wsl-compressed'][0])[0]
    packed=base64.b64decode(re.sub(rb'\s+',b'',export),validate=True);blob=gzip.decompress(packed)
    magic,version,size,count,recsize,first,last,crc,reserved=struct.unpack_from('<8sIIIIQQII',blob)
    assert (magic,version,size,count,recsize,reserved)==(b'EUDTXJ48',1,3120,512,6,0) and len(blob)==size and last-first+1==count
    check=bytearray(blob);check[40:44]=bytes(4);assert zlib.crc32(check)==crc
    wanted_export=base64.b64encode(blob);got_export=re.sub(rb'\s+',b'',re.search(rb'(?m)^RVVEVFhKNDg[A-Za-z0-9+/=]*\r?\n(?:[A-Za-z0-9+/=]+\r?\n)*',captures['wsl-journal-ready'][0])[0])
    holes=[i for i in range(len(wanted_export)-3) if wanted_export[:i]+wanted_export[i+4:]==got_export]
    assert len(holes)==1
    results[1]['export_missing_chars']=wanted_export[holes[0]:holes[0]+4].decode()
    results[1]['export_gap_base64_offset']=holes[0]
    records=[blob[48+i*6:54+i*6] for i in range(count)]
    expected=[]
    for r in records:
        n,source=r[:2];assert 1<=n<=4 and source in (1,2) and not any(r[2+n:])
        expected.append(bytes([0x90,n])+r[2:2+n])
    # Unique 16-frame anchors locate unchanged observed boundaries. The full
    # prefix/suffix are checked directly, including identical zero frames.
    anchors=[]
    for i in range(count-15):
        matches=[j for j in range(len(frames)-15) if frames[j:j+16]==expected[i:i+16]]
        if len(matches)==1:anchors.append((i,matches[0]))
    assert anchors
    lo=anchors[0][1]-anchors[0][0];hi=anchors[-1][1]+count-anchors[-1][0]
    assert lo>=0 and hi<=len(frames)
    observed=frames[lo:hi]
    i=j=0;gaps=[]
    while i<len(expected) and j<len(observed):
        if expected[i]==observed[j]:i+=1;j+=1;continue
        # Keep every received frame unchanged. Anchor the next surviving run
        # of at least 16 records; report ambiguous intervals without filling.
        choices=[(k,l) for k,l in anchors if k>i and l-lo>=j]
        k,l=min(choices,key=lambda x:x[1])
        l-=lo
        gaps.append(dict(first_seq=first+i,last_seq=first+k-1,expected_records=k-i,observed_records=l-j,
            expected_wire=[f.hex() for f in expected[i:k]],observed_wire=[f.hex() for f in observed[j:l]],
            expected_payload=b''.join(f[2:] for f in expected[i:k]).decode(),observed_payload=b''.join(f[2:] for f in observed[j:l]).decode()))
        i=k;j=l
    assert expected[i:]==observed[j:]
    missing=[]
    for gap in gaps:
        indexes=[]
        for wire in gap['observed_wire']:
            found=[k for k,w in enumerate(gap['expected_wire']) if w==wire]
            assert len(found)==1;indexes.append(found[0])
        assert indexes==sorted(indexes) and len(indexes)==len(set(indexes))
        for k,wire in enumerate(gap['expected_wire']):
            if k not in indexes:
                seq=gap['first_seq']+k
                missing.append(dict(seq=seq,source=records[seq-first][1],wire=wire))
    assert len(missing)==count-len(observed)==9
    missing_payload=sum(sum(len(bytes.fromhex(f))-2 for f in g['expected_wire'])-sum(len(bytes.fromhex(f))-2 for f in g['observed_wire']) for g in gaps)
    result=dict(captures=results,journal=dict(first_seq=first,last_seq=last,crc=f'{crc:08x}',sha256=sha256(blob).hexdigest(),
        bytes=len(blob),compressed_bytes=len(packed),crc_valid=True,expected_frames=count,observed_frames=len(observed),
        raw_start_frame=lo,missing_frames=count-len(observed),missing_payload_bytes=missing_payload,missing_records=missing,anchored_intervals=gaps),
        limits='Virtual HCD completions do not prove physical USB ACK. CPU journal proves issued software values, not hardware delivery. '
        'This WSL bypasses qcusbser, but still uses Windows USB/IP and the lower USB stack. Only one busy-console LEN14 probe was run; global stability remains open.')
    if a.out:
        a.out.write_text(json.dumps(result,indent=2)+'\n')
        (a.out.parent/'wsl-full-journal.bin').write_bytes(blob)
    print(json.dumps(result))
if __name__=='__main__':main()
