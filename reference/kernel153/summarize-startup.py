"""Extract only display evidence from the retained private startup archive."""
from pathlib import Path
import collections, hashlib, json, re, tarfile

private = Path('/mnt/e/edk2-samurai-out/kernel153')
archive = private/'first-startup-private.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == '4c7b7393a1ab4f0aa7fcaaa5e2f81b7f5603633281847b99c7f62b68d35dfc76'
totals,raw,first,last = {}, collections.Counter(), {}, {}
detail=private/'display-startup-events-private.txt'
with tarfile.open(archive) as tar, detail.open('w') as output:
    for name in ['early-trace-private.txt','early-snapshot-private.txt','live-trace-private.txt','residual-trace-private.txt']:
        counts=collections.Counter()
        for line in tar.extractfile('k153-first-startup/'+name):
            text=line.decode()
            match=re.search(r'(\d+\.\d+): (msm_dsi_error\w+|dpu_\w+): (.*)',text)
            if not match: continue
            stamp,event,params=match.groups()
            counts[event]+=1
            key=name+'/'+event
            first.setdefault(key,float(stamp));last[key]=float(stamp)
            if event=='msm_dsi_error_status':raw[params]+=1
            output.write(name+' '+text)
        totals[name]=dict(counts)
report=dict(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    totals=totals,first=first,last=last,raw_status_counts=dict(raw),private_event_file=str(detail))
(private/'startup-trace-summary-private.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
