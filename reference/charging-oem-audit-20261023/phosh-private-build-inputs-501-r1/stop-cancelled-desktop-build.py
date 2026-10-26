"""User cancellation: one normal SIGINT to the current owned Ninja only."""
from pathlib import Path
import hashlib
import json
import os
import signal

BASE=Path('/home/cy122/charging-management-20261023/phosh-external-power-build-501-r1')
ROOT=BASE/'root'
state=json.loads((BASE/'installed-target-build-state-private.json').read_bytes())
assert state['terminal'] is False
parent=state['pid']

def identity(pid):
    p=Path('/proc',str(pid));s=(p/'stat').read_text().rsplit(')',1)[1].split()
    return {'pid':pid,'ppid':int(s[1]),'state':s[0],'startticks':int(s[19]),
            'argv':[v.decode() for v in (p/'cmdline').read_bytes().split(b'\0') if v],
            'root':os.readlink(p/'root'),'comm':(p/'comm').read_text().strip()}

procs={}
for p in Path('/proc').glob('[0-9]*'):
    try:procs[int(p.name)]=identity(int(p.name))
    except (FileNotFoundError,ProcessLookupError):pass
assert parent in procs
owned={parent}
for _ in range(20):
    previous=set(owned);owned.update(pid for pid,r in procs.items() if r['ppid'] in owned)
    if previous==owned:break
rows=[procs[pid] for pid in owned if pid in procs]
ninjas=[p for p in rows if p['comm']=='ninja' and p['root']==str(ROOT) and '/work/build/phosh-external-power' in p['argv']]
assert len(ninjas)==1,ninjas
ninja=ninjas[0]
assert identity(ninja['pid'])==ninja
record={'owned_outer':state,'descendants_before':rows,'signalled':ninja,'signal':'SIGINT',
        'only_one_ninja_signalled':True,'no_compiler_or_process_group_killed':True,
        'reason':'user explicitly cancelled all desktop changes and Phosh build/package/test work',
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
out=BASE/'cancelled-desktop-sigint-private.json'
assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n')
os.kill(ninja['pid'],signal.SIGINT)
print(json.dumps({'SIGINT_sent_once':True,'ninja_pid':ninja['pid'],'ninja_startticks':ninja['startticks'],
                  'outer_pid':parent,'descendant_count':len(rows),'no_new_build_started':True}))
