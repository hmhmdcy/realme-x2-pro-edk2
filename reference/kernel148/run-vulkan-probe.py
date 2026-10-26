"""Bounded Vulkan invocation; save a fresh fault before devcoredump expires."""
from pathlib import Path
import argparse, hashlib, json, os, subprocess, time
p=argparse.ArgumentParser(); p.add_argument('label'); p.add_argument('--frames',type=int,default=240)
p.add_argument('--delay',type=int,default=40); p.add_argument('--debug',default='')
p.add_argument('--driver',default=''); p.add_argument('--headless',action='store_true')
p.add_argument('--gsk-node',default=''); p.add_argument('--rd',action='store_true')
p.add_argument('--pause-ms',type=int,default=0)
p.add_argument('--session',default='',choices=['','cube','settings','settings-cycle'])
p.add_argument('--panel',default='display');p.add_argument('--memory',action='store_true')
p.add_argument('--replay-from',default='');p.add_argument('--parallel',default='',choices=['','vulkan','gles'])
p.add_argument('--variants',action='store_true');p.add_argument('--shrink-pages',type=int,default=0);p.add_argument('--phone-layout',action='store_true');p.add_argument('--draw-churn',action='store_true');a=p.parse_args()
assert a.label.replace('-','').isalnum() and 1<=a.frames<=10000 and 5<=a.delay<=180
assert 0<=a.shrink_pages<=256
os.umask(0o077); out=Path('/var/lib/samurai')/('k148-'+a.label); out.mkdir(mode=0o700)
boot=Path('/proc/sys/kernel/random/boot_id').read_bytes(); (out/'boot-id-private.txt').write_bytes(boot)
def capture(cmd,name):
    with (out/name).open('wb') as f: subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=30)
def counts():
    d=subprocess.check_output(['dmesg'],text=True)
    return {k:d.count(v) for k,v in {'gpu_faults':'gpu fault:','warnings':'WARNING:',
        'dpu_timeouts':'frame done timeout','dsi_errors':'dsi_err_worker','dma_prepare':'unable to prepare channel'}.items()}
def desktop(): return {n:subprocess.check_output(['pgrep','-x',n],text=True).strip() for n in ['phoc','phosh']}
before=counts(); pids=desktop(); assert Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
capture(['dmesg'],'dmesg-before-private.txt'); capture(['uname','-a'],'kernel.txt')
env=dict(os.environ,XDG_RUNTIME_DIR='/run/user/10000',WAYLAND_DISPLAY='wayland-0',
         LD_PRELOAD='/var/lib/samurai/k148-tools/vm-bind-tap.so',K148_IOCTL_LOG=str(out/'vm-bind-private.jsonl'))
if a.debug: env['TU_DEBUG']=a.debug
else:env.pop('TU_DEBUG',None)
if a.driver: env['VK_DRIVER_FILES']=a.driver
driver_library=Path(json.loads(Path(a.driver).read_text())['ICD']['library_path']) if a.driver else Path('/usr/lib/libvulkan_freedreno.so')
driver_hash=hashlib.sha256(driver_library.read_bytes()).hexdigest()
probe_hash=hashlib.sha256(Path('/var/lib/samurai/k148-tools/'+('vulkan-memory-probe' if a.memory else 'vulkan-pixel-probe')).read_bytes()).hexdigest() if a.headless and not a.session and not a.gsk_node else None
assert 0<=a.pause_ms<=5000
env['K148_PAUSE_MS']=str(a.pause_ms)
env['K148_VARIANTS']='1' if a.variants else '0'
assert not a.phone_layout or a.session
env['K148_PHONE_LAYOUT']='1' if a.phone_layout else '0'
assert not a.draw_churn or (a.headless and not a.session and not a.memory and not a.gsk_node)
env['K148_DRAW_CHURN']='1' if a.draw_churn else '0'
if a.rd:
    (out/'rd').mkdir(mode=0o700)
    env.update(FD_RD_DUMP='combine,full',FD_RD_DUMP_PATH=str(out/'rd'))
cmd=['/tmp/k148-sdk/usr/bin/vkcube','--wsi','wayland','--width','800','--height','600','--c',str(a.frames)]
if a.headless: cmd=['/var/lib/samurai/k148-tools/vulkan-pixel-probe',str(a.frames)]
if a.memory:
    assert a.headless
    env['K148_CAPTURE_OUTPUT']=str(out/'capture-addresses-private.txt')
    if a.replay_from:
        source=Path(a.replay_from).resolve()
        assert source.is_relative_to('/var/lib/samurai') and source.is_file()
        env['K148_CAPTURE_INPUT']=str(source)
    cmd=['/var/lib/samurai/k148-tools/vulkan-memory-probe',str(a.frames)]
else: assert not a.replay_from
if a.gsk_node:
    assert a.headless
    cmd=['gtk4-rendernode-tool','benchmark','--renderer=vulkan','--runs='+str(a.frames),a.gsk_node]
if a.session:
    assert a.headless
    cmd=['python3','/tmp/k148-headless-session.py',a.session,str(a.frames) if a.session=='cube' else a.panel]
if a.parallel:
    assert a.headless and not a.session and not a.memory and not a.gsk_node
    cmd=['python3','/tmp/k148-parallel-probe.py',a.parallel,str(a.frames)]
was_on=True
if not a.headless:
    display_env='env XDG_RUNTIME_DIR=/run/user/10000 WAYLAND_DISPLAY=wayland-0 '
    capture(['su','-s','/bin/sh','cy122','-c',display_env+'wlr-randr'],'output-before.txt')
    was_on='Enabled: yes' in (out/'output-before.txt').read_text()
    if not was_on: capture(['su','-s','/bin/sh','cy122','-c',display_env+'wlr-randr --output DSI-1 --on'],'output-on.txt')
start=time.monotonic(); saved=set(); error=None; child=None; observed=0; shrink_results=[]; enabled_events=[]
trace=Path('/sys/kernel/tracing/instances')/('k148-'+a.label);trace.mkdir()
(trace/'tracing_on').write_text('0');(trace/'buffer_size_kb').write_text('512');(trace/'trace_clock').write_text('boot')
for event in ['msm_gpu_suspend','msm_gpu_resume','msm_gpu_vm_update','msm_gpu_vm_switch_enqueue','msm_gpu_submit','msm_gpu_submit_retired','msm_gem_shrink']:
    e=trace/'events/drm_msm_gpu'/event/'enable'
    if e.exists():e.write_text('1');enabled_events.append(event)
(trace/'tracing_on').write_text('1')
try:
    with (out/'vulkan-private.log').open('wb') as log:
        child=subprocess.Popen(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
        deadline=start+(100 if a.session else min(180,max(30,a.frames*.7 if a.gsk_node else a.frames*(a.pause_ms/1000+.2)+10)))
        while child.poll() is None:
            if time.monotonic()>deadline: child.terminate(); raise TimeoutError('Bounded Vulkan workload timed out')
            if a.shrink_pages and len(shrink_results)<4 and time.monotonic()-start>.5+len(shrink_results)*2:
                shrink=Path('/sys/kernel/debug/dri/1/shrink')
                assert shrink.is_file() and shrink.parent.joinpath('gpu').is_file()
                shrink.write_text(str(a.shrink_pages))
                value=int(shrink.read_text().strip(),16)
                shrink_results.append(dict(requested_pages=a.shrink_pages,
                    reported_freed_pages=None if value==2**64-1 else value,stop=value==2**64-1))
            for dev in Path('/sys/class/devcoredump').glob('devcd*'):
                if dev.name not in saved:
                    capture(['cat',str(dev/'data')],dev.name+'-private.data'); saved.add(dev.name)
            time.sleep(.5)
        rc=child.returncode
        for _ in range(a.delay):
            for dev in Path('/sys/class/devcoredump').glob('devcd*'):
                if dev.name not in saved:
                    capture(['cat',str(dev/'data')],dev.name+'-private.data'); saved.add(dev.name)
            time.sleep(1)
            observed+=1
except BaseException as e:
    error={'type':type(e).__name__,'message':str(e)}
finally:
    if child and child.poll() is None:
        child.terminate()
        try: child.wait(timeout=3)
        except subprocess.TimeoutExpired: child.kill(); child.wait()
    capture(['dmesg'],'dmesg-final-private.txt')
    (trace/'tracing_on').write_text('0');capture(['cat',str(trace/'trace')],'gpu-trace-private.txt')
    stats={x.parent.name:x.read_text() for x in (trace/'per_cpu').glob('cpu*/stats')}
    (out/'trace-stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
    (trace/'events/enable').write_text('0');trace.rmdir()
    if not a.headless and not was_on:
        capture(['su','-s','/bin/sh','cy122','-c',display_env+'wlr-randr --output DSI-1 --off'],'output-restored.txt')
    records=[json.loads(l) for l in (out/'vm-bind-private.jsonl').read_text().splitlines()] if (out/'vm-bind-private.jsonl').exists() else []
    maps=[r for r in records if r['op']==1 and r['rc']==0]
    t=(out/'gpu-trace-private.txt').read_text()
    result=dict(label=a.label,debug=a.debug,frames=a.frames,headless=a.headless,memory=a.memory,session=a.session,panel=a.panel if a.session=='settings' else '',gsk_node=Path(a.gsk_node).name,raw_command_dump=a.rd,pause_ms=a.pause_ms,
        gpu_suspend_events=t.count('msm_gpu_suspend:'),gpu_resume_events=t.count('msm_gpu_resume:'),vm_switch_enqueue_events=t.count('msm_gpu_vm_switch_enqueue:'),exit=child.returncode if child else None,
        error=error,before=before,after=counts(),vm_bind_ops=len(records),successful_maps=len(maps),
        successful_unmaps=sum(r['op']==0 and r['rc']==0 for r in records),
        unaligned64k_maps=sum(r['iova']%65536!=0 for r in maps),failed_bind_ops=sum(r['rc']!=0 for r in records),
        core_saved=len(saved),desktop_preserved=desktop()==pids,boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_bytes()==boot,
        taint=Path('/proc/sys/kernel/tainted').read_text().strip(),elapsed_seconds=time.monotonic()-start,
        delayed_observation_seconds=observed,driver_override=bool(a.driver),driver_library_sha256=driver_hash,parallel=a.parallel,external_capture_replay=bool(a.replay_from),pixel_variants=a.variants,
        enabled_trace_events=enabled_events,shrink_operations=shrink_results,shrink_trace_events=t.count('msm_gem_shrink:'),probe_binary_sha256=probe_hash,phone_layout=a.phone_layout,draw_churn=a.draw_churn)
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    (out/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  ./'+f.name+'\n' for f in sorted(out.iterdir()) if f.is_file() and f.name!='SHA256SUMS'))
    subprocess.run(['tar','-C',str(out),'-czf','/tmp/k148-'+a.label+'-private.tar.gz','.'],check=True,timeout=40)
    print(json.dumps(result),flush=True)
    if error: raise SystemExit(2)
