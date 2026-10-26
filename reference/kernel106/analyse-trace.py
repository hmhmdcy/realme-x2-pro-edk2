from pathlib import Path,PurePosixPath
import collections,hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel106')
def read_archive(name):
    files={}
    with tarfile.open(out/(name+'.tar')) as t:
        for m in t:
            assert not m.issym() and not m.islnk()
            if not m.isfile():continue
            p=PurePosixPath(m.name)
            assert p.parts[0]=='k106-'+name and not p.is_absolute() and '..' not in p.parts
            n=str(PurePosixPath(*p.parts[1:]));assert n not in files
            files[n]=t.extractfile(m).read()
    seen=set()
    for l in files['SHA256SUMS'].decode().splitlines():
        h,n=l.split('  ',1);n=n.removeprefix('./')
        assert n not in seen and hashlib.sha256(files[n]).hexdigest()==h;seen.add(n)
    assert seen==files.keys()-{'SHA256SUMS'}
    return files
def analyse(name):
    f=read_archive(name);trace=f['trace.txt'].decode()
    events=collections.Counter(re.findall(r'\d+\.\d+: ([a-zA-Z0-9_]+):',trace))
    lost={n:{k:int(v) for k,v in re.findall(r'^(overrun|commit overrun|dropped events):\s*(\d+)',b.decode(),re.M)} for n,b in f.items() if n.endswith('-stats.txt')}
    tx=[]
    for l in trace.splitlines():
        m=re.search(r'(\d+\.\d+): qrtr_endpoint_tx: node=(\d+) wire_node=(\d+) type=(\d+) src_port=(\d+) dst_port=(\d+) bytes=(\d+) result=(-?\d+)',l)
        if m:tx.append(dict(zip(['time','node','wire_node','type','src_port','dst_port','bytes','result'],[float(m[1])]+[int(x) for x in m.groups()[1:]])))
    txcounts=collections.Counter((e['node'],e['wire_node'],e['type'],e['result']) for e in tx)
    selected=[]
    for l in trace.splitlines():
        if any(n in l for n in ['qrtr_ns_message:','qrtr_ns_server_add:','qrtr_ns_service_announce_new:','samurai_pdm_response:','samurai_qrtr_rx_drop:','samurai_core_transaction:']):
            selected.append(l[l.index(': ',l.index('...'))+2:] if '...' in l else l.strip())
    # Only protocol metadata; raw trace and process/boot identities stay private.
    report=dict(archive=name,verified_files=len(f)-1,trace_bytes=len(f['trace.txt']),events=dict(events),lost=lost,hello=[e for e in tx if e['type']==2],tx_counts=[dict(node=n,wire_node=w,type=t,result=r,count=c) for (n,w,t,r),c in sorted(txcounts.items())],selected_protocol_metadata=selected)
    (out/(name+'-trace-analysis.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ['archive','verified_files','trace_bytes','events','lost','hello','tx_counts']},indent=2))
    print('\n'.join(selected[:100]))
    return report
if __name__=='__main__':
    import sys
    for n in sys.argv[1:]:analyse(n)
