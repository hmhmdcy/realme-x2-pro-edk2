"""One new-boot recorder, retaining early bootconfig traces and live events."""
from pathlib import Path
import hashlib,json,os,re,subprocess,time
os.umask(0o077)
base=Path('/var/lib/samurai/k162-tools')
out=Path('/var/lib/samurai/k162-first-startup')
trace=Path('/sys/kernel/tracing/instances/k162-startup')
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes()
assert os.uname().version.startswith('#158 ')
assert boot != Path('/var/lib/samurai/k162-preflash/boot-id-private.txt').read_bytes()
assert not out.exists() and not trace.exists()
out.mkdir(mode=0o700)
(out/'boot-id-private.txt').write_bytes(boot)
def capture(args,name):
    r=subprocess.run(args,capture_output=True,timeout=20)
    (out/name).write_bytes(r.stdout+r.stderr)
    return r.returncode
def counts(log):
    return {k:log.count(v) for k,v in dict(kms_init_failures='kms hw init failed',dpu_timeouts='frame done timeout',
        dsi_errors='dsi_err_worker',gpu_faults='gpu fault:',warnings='WARNING:',dma_prepare='unable to prepare channel').items()}
capture(['dmesg'],'dmesg-before-private.txt')
for name in ['trace','snapshot']:
    capture(['cat','/sys/kernel/tracing/instances/display/'+name],'early-'+name+'-private.txt')
early_stats={p.parent.name:p.read_text() for p in Path('/sys/kernel/tracing/instances/display/per_cpu').glob('cpu*/stats')}
(out/'early-stats.json').write_text(json.dumps(early_stats,indent=2))
events=[('drm_msm_dsi',n) for n in ['msm_dsi_error_irq','msm_dsi_error_status','msm_dsi_error_work']]
events += [('drm_panel','drm_panel_backlight'),('dpu','dpu_first_frame_backlight')]
events += [('dpu',n) for n in ['dpu_enc_frame_watchdog','dpu_enc_frame_done_timeout','dpu_enc_frame_done_cb',
    'dpu_enc_phys_cmd_pp_tx_done','dpu_enc_kickoff','dpu_enc_rc']]
trace.mkdir()
reader=None;error=None;rows=[];snapshots=[];snapshot_phases=set();started=time.monotonic()
try:
    (trace/'tracing_on').write_text('0')
    (trace/'buffer_size_kb').write_text('8192')
    (trace/'trace_clock').write_text('boot')
    for system,name in events:(trace/'events'/system/name/'enable').write_text('1')
    with (out/'live-trace-private.txt').open('wb') as f:
        reader=subprocess.Popen(['cat',str(trace/'trace_pipe')],stdout=f,stderr=subprocess.DEVNULL)
        (trace/'tracing_on').write_text('1')
        (trace/'trace_marker').write_text('K162_STARTUP_RECORDER_READY\n')
        (out/'ready.json').write_text(json.dumps(dict(uptime=Path('/proc/uptime').read_text().split()[0],
            kernel_build=158,events=events)))
        for i in range(19):
            assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot
            log=subprocess.check_output(['dmesg'],text=True)
            card=Path('/dev/dri/by-path/platform-ae01000.display-controller-card')
            state_path=Path('/sys/kernel/debug/dri')/card.resolve().name.removeprefix('card')/'state'
            state=state_path.read_text() if state_path.exists() else ''
            pids={n:bool(subprocess.run(['pgrep','-u','10000','-x',n],capture_output=True).stdout) for n in ['phoc','phosh']}
            active='\n\tactive=1\n' in state
            phases=[]
            if active and 'fbcon-first' not in snapshot_phases:phases.append('fbcon-first')
            if active and all(pids.values()) and 'desktop-first' not in snapshot_phases:phases.append('desktop-first')
            for phase in phases:
                for repeat in range(2):
                    pre=state_path.read_text()
                    rc=capture(['cat',str(state_path.parent/'kms')],f'kms-{phase}-{repeat}-private.txt')
                    post=state_path.read_text()
                    valid=rc==0 and '\n\tactive=1\n' in pre and '\n\tactive=1\n' in post
                    (out/f'kms-{phase}-{repeat}-state-before-private.txt').write_text(pre)
                    (out/f'kms-{phase}-{repeat}-state-after-private.txt').write_text(post)
                    snapshots.append(dict(phase=phase,repeat=repeat,uptime=float(Path('/proc/uptime').read_text().split()[0]),
                        valid_active_before_and_after=valid,returncode=rc,counts=counts(subprocess.check_output(['dmesg'],text=True))))
                    time.sleep(0.25)
                snapshot_phases.add(phase)
                (out/'snapshot-validation.json').write_text(json.dumps(snapshots,indent=2)+'\n')
            rows.append(dict(index=i,elapsed=time.monotonic()-started,uptime=float(Path('/proc/uptime').read_text().split()[0]),
                counts=counts(log),desktop=pids,taint=int(Path('/proc/sys/kernel/tainted').read_text()),crtc_active='\n\tactive=1\n' in state))
            (out/'samples.json').write_text(json.dumps(rows,indent=2)+'\n')
            if i<18:time.sleep(5)
except BaseException as exc:error=dict(type=type(exc).__name__,message=str(exc))
finally:
    (trace/'tracing_on').write_text('0')
    if reader:
        reader.terminate();reader.wait(timeout=5)
    capture(['cat',str(trace/'trace')],'residual-trace-private.txt')
    stats={p.parent.name:p.read_text() for p in (trace/'per_cpu').glob('cpu*/stats')}
    (out/'stats.json').write_text(json.dumps(stats,indent=2))
    (trace/'events/enable').write_text('0')
    trace.rmdir()
    capture(['dmesg'],'dmesg-after-private.txt')
    card=Path('/dev/dri/by-path/platform-ae01000.display-controller-card').resolve()
    capture(['cat',str(Path('/sys/kernel/debug/dri')/card.name.removeprefix('card')/'state')],'drm-final-private.txt')
    result=dict(kernel_build=158,sample_count=len(rows),error=error,trace_removed=not trace.exists(),
        counts_after=counts((out/'dmesg-after-private.txt').read_text()),
        trace_loss_free=all(int(re.search(r'^'+re.escape(n)+r':\s*(\d+)',s,re.M)[1])==0
            for s in stats.values() for n in ['overrun','commit overrun','dropped events']),
        first_sample_uptime=rows[0]['uptime'] if rows else None,
        bootconfig_early_trace_saved=True,recorder_started_as_boot_service=True,elapsed_seconds=time.monotonic()-started)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'complete').write_text('complete\n')
    print(json.dumps(result),flush=True)
