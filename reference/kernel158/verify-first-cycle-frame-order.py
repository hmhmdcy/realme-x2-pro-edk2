from pathlib import Path
import json,re,tarfile
out=Path('/mnt/e/edk2-samurai-out/kernel158');ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel158')
with tarfile.open(out/'first-evidence-private.tar.gz') as t:
    s=t.extractfile('k158-standard-dpms/display-trace-private.txt').read().decode()
events=[]
for l in s.splitlines():
    m=re.search(r'(\d+\.\d+): (dpu_first_frame_backlight|drm_panel_backlight|dpu_enc_phys_cmd_pp_tx_done): (.*)',l)
    if m:events.append((float(m[1]),m[2],m[3]))
events.sort();pending=False;tx=None;wait=None;gates=[]
for stamp,name,detail in events:
    if name=='dpu_enc_phys_cmd_pp_tx_done':tx=stamp
    elif name=='dpu_first_frame_backlight':wait=(stamp,int(re.search(r'ret=(-?\d+)',detail)[1]))
    elif 'phase=0' in detail:pending=True;tx=None;wait=None
    elif 'phase=2' in detail:pending=False;tx=None;wait=None
    elif 'phase=1' in detail:
        gates.append(dict(pending_seen=pending,tx_done_seen=tx is not None,wait_ret=wait[1] if wait else None,
            tx_to_ready_ms=(stamp-tx)*1000 if tx else None))
        pending=False
assert len(gates)==12
assert all(g['pending_seen'] and g['tx_done_seen'] and g['wait_ret']==0 and g['tx_to_ready_ms']>=0 for g in gates)
result=dict(stage=158,actual_kernel_build=158,real_hardware_gate_count=12,all_after_tx_done=True,gates=gates,
    physical_wake_user_confirmed_no_flicker=True)
(ref/'first-frame-order-validation.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result),flush=True)
