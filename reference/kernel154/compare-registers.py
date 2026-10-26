from pathlib import Path
import collections,hashlib,json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel154')
p=out/'register-ab-private.tar.gz'
assert hashlib.sha256(p.read_bytes()).hexdigest()=='fc745dc53869f0522e69db01149e1a3c1b942112458ea32cabaf4a2875b321e0'
def parse(text):
    section=None;regs={}
    for line in text.splitlines():
        m=re.fullmatch(r'=+(.*?)=+',line)
        if m:section=m[1];continue
        m=re.match(r'0x([0-9a-f]+) : ((?:[0-9a-f]{8} ?)+)$',line)
        if m:
            for i,value in enumerate(m[2].split()):regs[(section,int(m[1],16)+i*4)]=value
    return regs
with tarfile.open(p) as tar:
    before_state=tar.extractfile('k154-failure-before-recovery/drm-private.txt').read().decode()
    after_state=tar.extractfile('k154-after-recovery/drm-private.txt').read().decode()
    before=parse(tar.extractfile('k154-failure-before-recovery/kms-private.txt').read().decode())
    after=parse(tar.extractfile('k154-after-recovery/kms-private.txt').read().decode())
valid='\n\tactive=1\n' in before_state and '\n\tactive=1\n' in after_state
(out/'register-comparison-validity.json').write_text(json.dumps(dict(
    both_snapshots_active=valid,valid_for_fault_vs_recovery_comparison=valid,
    reason=None if valid else 'The first KMS snapshot was taken after automatic display blanking.'),indent=2)+'\n')
if not valid:
    print('K154_COMPARISON_REJECTED_INACTIVE_FIRST_SNAPSHOT')
    raise SystemExit(2)
changes=[]
for (section,address),value in before.items():
    updated=after.get((section,address))
    if updated!=value:changes.append(dict(section=section,offset=hex(address),before=value,after=updated))
(out/'register-ab-diff-private.json').write_text(json.dumps(changes,indent=2)+'\n')
summary=collections.Counter(row['section'] for row in changes)
print(json.dumps(dict(changed_by_section=dict(summary),dsi_changes=[r for r in changes if r['section']=='dsi0_ctrl'],
    dsc_and_ctl=[r for r in changes if re.search(r'dsc|ctl|mdp|top',r['section'] or '',re.I)]),indent=2))
