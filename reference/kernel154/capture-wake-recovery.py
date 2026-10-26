"""Bounded standard DPMS recovery, retaining raw DSI and DPU events."""
from pathlib import Path
import hashlib, json, os, re, subprocess, time

os.umask(0o077)
out = Path('/var/lib/samurai/k154-wake-recovery')
trace = Path('/sys/kernel/tracing/instances/k154-wake-recovery')
boot_path = Path('/proc/sys/kernel/random/boot_id')
boot = boot_path.read_bytes()
assert os.uname().version.startswith('#154 ')
assert not out.exists() and not trace.exists()
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
card = Path('/dev/dri/by-path/platform-ae01000.display-controller-card').resolve(strict=True)
debug = Path('/sys/kernel/debug/dri')/card.name.removeprefix('card')
tool = ['python3', '/var/lib/samurai/k154-tools/display-power.py']

def capture(args, name):
    r = subprocess.run(args, capture_output=True, timeout=15)
    (out/name).write_bytes(r.stdout+r.stderr)
    r.check_returncode()
    return r.stdout.decode()

def counts(log):
    return {k: log.count(v) for k,v in dict(dpu_timeouts='frame done timeout',
        dsi_errors='dsi_err_worker', gpu_faults='gpu fault:', warnings='WARNING:',
        dma_prepare='unable to prepare channel').items()}

def pids():
    return {n:subprocess.check_output(['pgrep','-u','10000','-x',n],text=True).split()
        for n in ['phoc','phosh']}

before = counts(capture(['dmesg'], 'dmesg-before-private.txt'))
original_pids = pids()
prior = capture(tool+['get'], 'power-before-private.txt').strip()
events = [('drm_msm_dsi', n) for n in ['msm_dsi_error_irq','msm_dsi_error_status','msm_dsi_error_work']]
events += [('dpu', n) for n in ['dpu_enc_frame_done_timeout','dpu_enc_frame_done_cb',
    'dpu_enc_phys_cmd_pp_tx_done','dpu_enc_kickoff','dpu_enc_trigger_start',
    'dpu_enc_rc','dpu_crtc_disable','dpu_perf_crtc_update','dpu_core_perf_update_clk']]
trace.mkdir()
rows, error = [], None
try:
    (trace/'tracing_on').write_text('0')
    (trace/'buffer_size_kb').write_text('4096')
    (trace/'trace_clock').write_text('boot')
    for system,name in events: (trace/'events'/system/name/'enable').write_text('1')
    (trace/'tracing_on').write_text('1')
    for index,(state,seconds) in enumerate([('off',1),('on',5),('off',1),('on',8)]):
        assert boot_path.read_bytes() == boot and pids() == original_pids
        assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
        (trace/'trace_marker').write_text(f'K154_RECOVERY {index} {state} begin\n')
        capture(tool+[state], f'power-{index}-{state}-private.txt')
        for sample in range(seconds):
            time.sleep(1)
            drm = (debug/'state').read_text()
            (out/f'drm-{index}-{sample}-private.txt').write_text(drm)
            row = dict(index=index,sample=sample,state=state,
                uptime=float(Path('/proc/uptime').read_text().split()[0]),
                active='\n\tactive=1\n' in drm,
                actual_mdp_clock=int(Path('/sys/kernel/debug/clk/disp_cc_mdss_mdp_clk/clk_rate').read_text()),
                perf_clock=int((debug/'debug/core_perf/core_clk_rate').read_text()),
                counts=counts(subprocess.check_output(['dmesg'],text=True)))
            rows.append(row)
            (out/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
            assert row['active'] == (state=='on'), row
except BaseException as exc:
    error=dict(type=type(exc).__name__,message=str(exc))
finally:
    capture(tool+['on'], 'final-output-on-private.txt')
    (trace/'tracing_on').write_text('0')
    capture(['cat',str(trace/'trace')], 'trace-private.txt')
    stats = {p.parent.name:p.read_text() for p in (trace/'per_cpu').glob('cpu*/stats')}
    (out/'stats.json').write_text(json.dumps(stats,indent=2)+'\n')
    (trace/'events/enable').write_text('0')
    trace.rmdir()
    after=counts(capture(['dmesg'],'dmesg-after-private.txt'))
    result=dict(kernel_build=154,error=error,samples=len(rows),counts_before=before,counts_after=after,
        same_boot=boot_path.read_bytes()==boot,pids_preserved=pids()==original_pids,
        taint=int(Path('/proc/sys/kernel/tainted').read_text()),
        prior_power=prior,final_output_on=True,trace_removed=not trace.exists(),
        trace_loss_free=all(int(re.search(r'^'+re.escape(n)+r':\s*(\d+)',s,re.M)[1])==0
            for s in stats.values() for n in ['overrun','commit overrun','dropped events']),
        optical_visibility_verified=False)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    if error: raise SystemExit(1)
