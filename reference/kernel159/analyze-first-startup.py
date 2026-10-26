from pathlib import Path
import hashlib,json,re,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel159');out=Path('/mnt/e/edk2-samurai-out/kernel159')
with tarfile.open(out/'first-evidence-private.tar.gz') as t:
    d=t.extractfile('k159-first-runtime/dmesg-private.txt').read().decode()
    early=t.extractfile('k159-first-startup/early-trace-private.txt').read().decode()
    early_stats=json.loads(t.extractfile('k159-first-startup/early-stats.json').read())
    assert d.index('DSI firmware stop before PHY: CTRL=0x1f5 -> 0x0')<d.index('boot CTL0:')<d.index('boot CTL0 cleared:')
    assert d.count('DSI firmware stop before PHY:')==1
    rows=[]
    for line in early.splitlines():
        m=re.search(r'(\d+\.\d+): (dpu_first_frame_backlight|dpu_enc_phys_cmd_pp_tx_done): (.*)',line)
        if m:rows.append((float(m[1]),m[2],m[3]))
    rows.sort();tx=None;startup=[]
    for stamp,name,detail in rows:
        if name=='dpu_enc_phys_cmd_pp_tx_done':tx=stamp
        else:
            ret=int(re.search(r'ret=(-?\d+)',detail)[1])
            startup.append(dict(ret=ret,tx_done_seen=tx is not None,tx_done_to_wait_ms=(stamp-tx)*1000 if tx else None))
    assert startup and all(r['ret']==0 and r['tx_done_seen'] and r['tx_done_to_wait_ms']>=0 for r in startup)
    lossfree=all(int(re.search(r'^'+re.escape(n)+r':\s*(\d+)',s,re.M)[1])==0
        for s in early_stats.values() for n in ['overrun','commit overrun','dropped events'])
    assert lossfree
    s=t.extractfile('k159-standard-dpms/display-trace-private.txt').read().decode()
    events=[]
    for line in s.splitlines():
        m=re.search(r'(\d+\.\d+): (dpu_first_frame_backlight|drm_panel_backlight|dpu_enc_phys_cmd_pp_tx_done): (.*)',line)
        if m:events.append((float(m[1]),m[2],m[3]))
    events.sort();pending=False;tx=None;wait=None;gates=[]
    for stamp,name,detail in events:
        if name=='dpu_enc_phys_cmd_pp_tx_done':tx=stamp
        elif name=='dpu_first_frame_backlight':wait=(stamp,int(re.search(r'ret=(-?\d+)',detail)[1]))
        elif 'phase=0' in detail:pending=True;tx=None;wait=None
        elif 'phase=2' in detail:pending=False;tx=None;wait=None
        elif 'phase=1' in detail:
            gates.append(dict(pending_seen=pending,tx_done_seen=tx is not None,wait_ret=wait[1] if wait else None,
                tx_to_ready_ms=(stamp-tx)*1000 if tx else None));pending=False
    assert len(gates)==12 and all(g['pending_seen'] and g['tx_done_seen'] and g['wait_ret']==0 and g['tx_to_ready_ms']>=0 for g in gates)
result=dict(stage=159,actual_kernel_build=158,same_image_second_boot=True,
    firmware_stop_before_ctl_success=True,one_shot_stop_count=1,early_trace_loss_free=lossfree,
    initial_tx_wait_after_pp_done=startup,wake_gate_count=12,all_wake_ready_after_successful_tx=True,gates=gates,
    record_start_uptime=17.72,physical_startup_transition_pending=True,
    archive_sha256=hashlib.sha256((out/'first-evidence-private.tar.gz').read_bytes()).hexdigest())
(ref/'first-startup-order-validation.json').write_text(json.dumps(result,indent=2)+'\n')
for n in ['startup-validation.json','runtime-validation.json','cycles-validation.json','boot-timing-validation.json']:(ref/n).write_bytes((out/n).read_bytes())
print(json.dumps(result),flush=True)
