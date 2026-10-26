"""Collect sanitized results; leave raw memory addresses and identities private."""
from pathlib import Path
import hashlib, json, os, re
from datetime import datetime, timezone
os.umask(0o077)
base=Path('/var/lib/samurai')
results=[];operations=[]
for path in sorted(base.glob('k148-*/result.json')):
    row=json.loads(path.read_text())
    if not all(k in row for k in ['label','before','after']):
        if path.parent.name=='k148-desktop-recovery':
            operations.append(dict(kind='desktop-recovery',**{k:row[k] for k in ['original_config_preserved','original_initial_session_restored','boot_preserved','config_sha256','taint'] if k in row}))
        continue
    # The early runner skipped the exit delay on timeout but reported the
    # requested delay. Preserve that original value and correct this summary.
    if row.get('error') and 'parallel' not in row:
        row['original_reported_delay_seconds']=row.get('delayed_observation_seconds')
        row['delayed_observation_seconds']=0
        row['early_timeout_delay_report_corrected']=True
    trace=path.parent/'gpu-trace-private.txt'
    if trace.exists():
        samples=[tuple(map(int,m)) for m in re.findall(r'msm_gem_shrink: nr_to_scan=(\d+) pg, purged=(\d+) pg, evicted=(\d+) pg, active_purged=(\d+) pg, active_evicted=(\d+) pg',trace.read_text(errors='replace'))]
        if samples:row['reclaim_trace_pages']=dict(purged=sum(m[1] for m in samples),evicted=sum(m[2] for m in samples),active_purged=sum(m[3] for m in samples),active_evicted=sum(m[4] for m in samples))
    log=path.parent/'vulkan-private.log'
    if log.exists():
        text=log.read_text(errors='replace')
        pixels=re.search(r'ALL_PIXELS_PASS iterations=(\d+) pixels=(\d+)', text)
        row['pixel_check']=dict(iterations=int(pixels[1]),pixels=int(pixels[2])) if pixels else None
        row['memory_check_passed']='MEMORY_PASS' in text
        row['capture_replay_checks']=[dict(iteration=int(a),external=bool(int(b)),aligned64k=bool(int(c)),mismatches=int(d))
            for a,b,c,d in re.findall(r'CAPTURE_REPLAY iteration=(\d+) external=(\d+) address_64k_aligned=(\d+) mismatches=(\d+)',text)]
    parallel=path.parent/'parallel-result.json'
    settings=path.parent/'settings-cleanup.json'
    if settings.exists():row['settings_cleanup']=json.loads(settings.read_text())
    session=path.parent/'session-app-result.json'
    if session.exists():row['session_app_result']=json.loads(session.read_text())
    if parallel.exists():
        row['parallel_result']=json.loads(parallel.read_text())
        row['parallel_pixel_checks']=[]
        for f in sorted(path.parent.glob('parallel-*-private.log')):
            text=f.read_text(errors='replace')
            pixels=re.search(r'ALL_PIXELS_PASS iterations=(\d+) pixels=(\d+)',text)
            if pixels:row['parallel_pixel_checks'].append(dict(iterations=int(pixels[1]),pixels=int(pixels[2])))
    results.append(row)
installed=Path('/usr/lib/libvulkan_freedreno.so')
new_fault=any(r['after']['gpu_faults']>r['before']['gpu_faults'] for r in results)
closeout=base/'k148-closeout/closeout-public.json'
summary=dict(stage=148,status='closed_out' if closeout.exists() else 'active',collected_at=datetime.now(timezone.utc).isoformat(),original_fault_reproduced=None if new_fault else False,new_fault_seen=new_fault,candidate_promoted=False,
             kernel='147/software132',installed_driver_sha256=hashlib.sha256(installed.read_bytes()).hexdigest(),tests=results,operations=operations)
summary['successful_test_runs']=sum(r.get('exit')==0 and r.get('error') is None for r in results)
summary['failed_test_runs']=len(results)-summary['successful_test_runs']
if closeout.exists():summary['closeout']=json.loads(closeout.read_text())
dest=Path('/tmp/k148-results-public.json')
dest.write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps(dict(results=len(results),candidate_promoted=False,
                     installed_driver_sha256=summary['installed_driver_sha256'])))
