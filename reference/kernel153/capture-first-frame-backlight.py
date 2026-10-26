"""Runtime A/B for the stock panel's delay-until-first-frame requirement."""
from pathlib import Path
import json,os,re,subprocess,time
os.umask(0o077)
assert os.uname().version.startswith('#153 ')
out=Path('/var/lib/samurai/k153-first-frame-backlight')
trace=Path('/sys/kernel/tracing/instances/k153-first-frame-backlight')
assert not out.exists() and not trace.exists()
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
bl=Path('/sys/class/backlight/ae94000.dsi.0')
brightness=(bl/'brightness').read_text().strip()
assert int(brightness)>0
tool=['python3','/var/lib/samurai/k153-tools/display-power.py']
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
(out/'brightness-before.txt').write_text(brightness+'\n')
def call(state):subprocess.run(tool+[state],check=True,capture_output=True,timeout=10)
def counts(log):
    return {k:log.count(v) for k,v in dict(dpu_timeouts='frame done timeout',
        dsi_errors='dsi_err_worker',gpu_faults='gpu fault:',warnings='WARNING:').items()}
before=subprocess.check_output(['dmesg'],text=True)
(out/'dmesg-before-private.txt').write_text(before)
trace.mkdir();error=None;first_done=None;restore_uptime=None
try:
    (trace/'tracing_on').write_text('0')
    (trace/'buffer_size_kb').write_text('4096')
    (trace/'trace_clock').write_text('boot')
    for system,names in [('dpu',['dpu_enc_kickoff','dpu_enc_phys_cmd_pp_tx_done',
        'dpu_enc_frame_done_cb','dpu_enc_frame_done_timeout']),
        ('drm_msm_dsi',['msm_dsi_error_irq','msm_dsi_error_status','msm_dsi_error_work'])]:
        for name in names:(trace/'events'/system/name/'enable').write_text('1')
    (trace/'tracing_on').write_text('1')
    (trace/'trace_marker').write_text('K153_CONTROL_WAKE begin\n')
    call('off');time.sleep(1);call('on');time.sleep(3)
    (trace/'trace_marker').write_text('K153_DEFERRED_WAKE brightness_zero\n')
    (bl/'brightness').write_text('0')
    call('off');time.sleep(1)
    (trace/'trace_marker').write_text('K153_DEFERRED_WAKE on_begin\n')
    call('on')
    deadline=time.monotonic()+5
    while time.monotonic()<deadline:
        recent=(trace/'trace').read_text().split('K153_DEFERRED_WAKE on_begin',1)[1]
        match=re.search(r'(\d+\.\d+): dpu_enc_phys_cmd_pp_tx_done:',recent)
        if match:
            first_done=float(match[1]);break
        time.sleep(0.02)
    assert first_done is not None,'No successful first frame in 5 seconds'
    assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
    (trace/'trace_marker').write_text('K153_DEFERRED_WAKE first_frame_received restore_brightness\n')
    (bl/'brightness').write_text(brightness)
    restore_uptime=float(Path('/proc/uptime').read_text().split()[0])
    time.sleep(5)
except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc))
finally:
    (bl/'brightness').write_text(brightness)
    call('on')
    (trace/'tracing_on').write_text('0')
    (out/'trace-private.txt').write_text((trace/'trace').read_text())
    stats={p.parent.name:p.read_text() for p in (trace/'per_cpu').glob('cpu*/stats')}
    (out/'stats.json').write_text(json.dumps(stats,indent=2)+'\n')
    (trace/'events/enable').write_text('0');trace.rmdir()
    after=subprocess.check_output(['dmesg'],text=True)
    (out/'dmesg-after-private.txt').write_text(after)
    result=dict(kernel_build=153,error=error,first_frame_done_uptime=first_done,
        brightness_restore_uptime=restore_uptime,original_brightness_restored=(bl/'brightness').read_text().strip()==brightness,
        same_boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
        counts_before=counts(before),counts_after=counts(after),trace_removed=not trace.exists(),
        trace_loss_free=all(int(re.search(r'^'+re.escape(n)+r':\s*(\d+)',s,re.M)[1])==0
            for s in stats.values() for n in ['overrun','commit overrun','dropped events']),
        optical_comparison_pending=True)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
    if error:raise SystemExit(1)
