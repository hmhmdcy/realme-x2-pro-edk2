"""Check actual TX/illumination order and matched active boot register dumps."""
from pathlib import Path
import collections, hashlib, json, re, tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel156')
def get(tar,tail):
    names=[n for n in tar.getnames() if n.endswith(tail)]
    assert len(names)==1,(tail,names)
    return tar.extractfile(names[0]).read().decode()
def regs(text):
    section=None;result={}
    for line in text.splitlines():
        m=re.fullmatch(r'=+(.*?)=+',line)
        if m:section=m[1];continue
        m=re.match(r'0x([0-9a-f]+) : ((?:[0-9a-f]{8} ?)+)$',line)
        if m:
            for i,v in enumerate(m[2].split()):result[(section,int(m[1],16)+4*i)]=v
    assert result
    return result
with tarfile.open(out/'first-validation-private.tar.gz') as t:
    s=get(t,'display-trace-private.txt')
    events=[]
    for line in s.splitlines():
        m=re.search(r'(\d+\.\d+): (dpu_first_frame_backlight|drm_panel_backlight|dpu_enc_phys_cmd_pp_tx_done): (.*)',line)
        if m:events.append((float(m[1]),m[2],m[3]))
    events.sort()
    pending=False;wait=None;tx=None;gates=[]
    for stamp,name,detail in events:
        if name=='dpu_enc_phys_cmd_pp_tx_done':tx=stamp
        elif name=='dpu_first_frame_backlight':
            ret=int(re.search(r'ret=(-?\d+)',detail)[1]);wait=(stamp,ret)
        elif 'phase=0' in detail:pending=True;wait=None;tx=None
        elif 'phase=2' in detail:pending=False;wait=None;tx=None
        elif 'phase=1' in detail:
            gates.append(dict(pending_seen=pending,wait_ret=wait[1] if wait else None,
                tx_done_seen=tx is not None,tx_to_backlight_ms=(stamp-tx)*1000 if tx else None,
                wait_to_backlight_ms=(stamp-wait[0])*1000 if wait else None))
            pending=False
    result=dict(stage=156,actual_cycle_gate_count=len(gates),gates=gates,
        all_ready_after_successful_tx=bool(gates) and all(g['pending_seen'] and g['wait_ret']==0
            and g['tx_done_seen'] and g['tx_to_backlight_ms']>=0 for g in gates),
        physical_display_verification_pending=True)
    (out/'first-frame-order-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
with tarfile.open('/mnt/e/edk2-samurai-out/kernel155/first-startup-private.tar.gz') as a,tarfile.open(out/'startup-small-private.tar.gz') as b:
    comparison=[];private=[]
    for phase in ['fbcon-first','desktop-first']:
        valid=all('\n\tactive=1\n' in get(t,f'kms-{phase}-0-state-{side}-private.txt')
            for t in [a,b] for side in ['before','after'])
        assert valid,phase
        x=regs(get(a,f'kms-{phase}-0-private.txt'));y=regs(get(b,f'kms-{phase}-0-private.txt'))
        changes=[dict(section=k[0],offset=hex(k[1]),before=v,after=y.get(k))
            for k,v in x.items() if y.get(k)!=v]
        private.append(dict(phase=phase,changes=changes))
        comparison.append(dict(phase=phase,both_active_before_and_after=valid,
            register_counts=[len(x),len(y)],changes_by_section=dict(collections.Counter(r['section'] for r in changes))))
    (out/'matched-active-register-diff-private.json').write_text(json.dumps(private,indent=2)+'\n')
    (out/'matched-active-register-comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    print(json.dumps(comparison),flush=True)
