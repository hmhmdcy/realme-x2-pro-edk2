"""Bounded GPU experiment, retaining failure and post-exit evidence."""
from pathlib import Path
import argparse, hashlib, json, os, re, signal, subprocess, time

p = argparse.ArgumentParser()
p.add_argument('label')
p.add_argument('--driver', default='')
p.add_argument('--debug', default='gmem')
p.add_argument('--loops', type=int, default=16)
p.add_argument('--holes', type=int, choices=[0, 1], default=1)
p.add_argument('--variants', action='store_true')
p.add_argument('--delay', type=int, default=45)
p.add_argument('--timeout', type=int, default=90)
p.add_argument('--rd', action='store_true')
p.add_argument('--binary', default='/var/lib/samurai/k149-tools/vulkan-hole-probe')
p.add_argument('--kind', choices=['pixel','settings','gsk','gles','parallel','memory'], default='pixel')
p.add_argument('--pause-ms', type=int, default=0)
p.add_argument('--replay-from', default='')
p.add_argument('--trace', action='store_true')
a = p.parse_args()
assert a.label.replace('-', '').isalnum() and 1 <= a.loops <= 200
assert 5 <= a.delay <= 180 and 10 <= a.timeout <= 300
assert 0 <= a.pause_ms <= 5000 and (not a.replay_from or a.kind=='memory')
os.umask(0o077)
out = Path('/var/lib/samurai')/('k149-'+a.label)
out.mkdir(mode=0o700)
boot = Path('/proc/sys/kernel/random/boot_id').read_bytes()
(out/'boot-id-private.txt').write_bytes(boot)
def capture(command, name):
    with (out/name).open('wb') as f:
        subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, check=True, timeout=30)
def counts():
    d = subprocess.check_output(['dmesg'], text=True)
    return {k: d.count(v) for k, v in dict(gpu_faults='gpu fault:', warnings='WARNING:',
        dpu_timeouts='frame done timeout', dsi_errors='dsi_err_worker',
        dma_prepare='unable to prepare channel').items()}
def desktop():
    result={}
    for n in ['phoc','phosh']:
        query=subprocess.run(['pgrep','-x',n],capture_output=True,text=True)
        pids=[]
        for pid in query.stdout.split():
            try:
                status=Path('/proc')/pid/'status'
                if int(re.search(r'^Uid:\s+(\d+)',status.read_text(),re.M)[1])==10000:
                    pids.append(pid)
            except FileNotFoundError: pass
        result[n]=' '.join(sorted(pids))
    return result
before, original_pids = counts(), desktop()
assert all(original_pids.values()), 'Expected the physical user desktop'
(out/'desktop-pids-before-private.json').write_text(json.dumps(original_pids))
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
capture(['dmesg'], 'dmesg-before-private.txt')
env = dict(os.environ, LD_PRELOAD='/var/lib/samurai/k148-tools/vm-bind-tap.so',
    K148_IOCTL_LOG=str(out/'vm-bind-private.jsonl'), K149_HOLES=str(a.holes),
    K148_VARIANTS=str(int(a.variants)), K148_DRAW_CHURN='1', K148_PHONE_LAYOUT='1',
    K148_PAUSE_MS=str(a.pause_ms))
env.update(XDG_RUNTIME_DIR='/run/user/10000',WAYLAND_DISPLAY='wayland-0')
if a.driver: env['VK_DRIVER_FILES'] = a.driver
else: env.pop('VK_DRIVER_FILES', None)
if a.debug: env['TU_DEBUG'] = a.debug
else: env.pop('TU_DEBUG', None)
if a.rd:
    (out/'rd').mkdir(mode=0o700)
    env.update(FD_RD_DUMP='combine,full', FD_RD_DUMP_PATH=str(out/'rd'))
library = Path(json.loads(Path(a.driver).read_text())['ICD']['library_path']) if a.driver else Path('/usr/lib/libvulkan_freedreno.so')
saved, errors = set(), []
def cores():
    for dev in Path('/sys/class/devcoredump').glob('devcd*'):
        if dev.name in saved: continue
        try:
            capture(['cat', str(dev/'data')], dev.name+'-private.data')
            saved.add(dev.name)
            capture(['dmesg'], dev.name+'-dmesg-private.txt')
            capture(['cat', '/sys/kernel/debug/dri/1/gem'], dev.name+'-gem-private.txt')
        except (OSError, subprocess.SubprocessError) as e:
            errors.append(dict(core=dev.name, type=type(e).__name__))
start = time.monotonic()
child = None
error = None
command=[a.binary,str(a.loops)]
if a.kind=='settings': command=['python3','/tmp/k148-headless-session.py','settings-cycle','display']
elif a.kind in ['gsk','gles']:
    command=['gtk4-rendernode-tool','benchmark','--renderer='+('vulkan' if a.kind=='gsk' else 'gl'),
             '--runs='+str(a.loops),'/var/lib/samurai/k148-tools/gsk-effects.node']
elif a.kind=='parallel': command=['python3','/tmp/k148-parallel-probe.py','gles',str(a.loops)]
elif a.kind=='memory':
    command=['/var/lib/samurai/k148-tools/vulkan-memory-probe',str(a.loops)]
    env['K148_CAPTURE_OUTPUT']=str(out/'capture-addresses-private.txt')
    if a.replay_from:
        replay=Path(a.replay_from).resolve()
        assert replay.is_relative_to('/var/lib/samurai') and replay.is_file()
        env['K148_CAPTURE_INPUT']=str(replay)
trace=None
enabled_events=[]
if a.trace:
    trace=Path('/sys/kernel/tracing/instances')/('k149-'+a.label)
    trace.mkdir()
    (trace/'tracing_on').write_text('0')
    (trace/'buffer_size_kb').write_text('512')
    (trace/'trace_clock').write_text('boot')
    for event in ['msm_gpu_suspend','msm_gpu_resume','msm_gpu_submit','msm_gpu_submit_retired','msm_gem_shrink']:
        enable=trace/'events/drm_msm_gpu'/event/'enable'
        if enable.exists():
            enable.write_text('1');enabled_events.append(event)
    (trace/'tracing_on').write_text('1')
try:
    with (out/'probe-private.log').open('wb') as log:
        child = subprocess.Popen(command, env=env, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
        while child.poll() is None:
            cores()
            if time.monotonic()-start > a.timeout:
                raise TimeoutError('GPU experiment reached its workload deadline')
            time.sleep(.1)
except BaseException as e:
    error = dict(type=type(e).__name__, message=str(e))
finally:
    if child and child.poll() is None:
        os.killpg(child.pid, signal.SIGTERM)
        try: child.wait(timeout=3)
        except subprocess.TimeoutExpired:
            os.killpg(child.pid, signal.SIGKILL)
            child.wait(timeout=3)
    delay_start = time.monotonic()
    while time.monotonic()-delay_start < a.delay:
        cores()
        time.sleep(.2)
    observed = time.monotonic()-delay_start
    capture(['dmesg'], 'dmesg-final-private.txt')
    trace_text=''
    trace_overruns=None
    if trace:
        (trace/'tracing_on').write_text('0')
        capture(['cat',str(trace/'trace')],'gpu-trace-private.txt')
        trace_text=(out/'gpu-trace-private.txt').read_text()
        stats={x.parent.name:x.read_text() for x in (trace/'per_cpu').glob('cpu*/stats')}
        (out/'trace-stats-private.json').write_text(json.dumps(stats,indent=2)+'\n')
        trace_overruns=sum(int(re.search(r'^overrun:\s*(\d+)',s,re.M)[1]) for s in stats.values())
        (trace/'events/enable').write_text('0')
        trace.rmdir()
    rows = [json.loads(x) for x in (out/'vm-bind-private.jsonl').read_text().splitlines()] if (out/'vm-bind-private.jsonl').exists() else []
    maps = [r for r in rows if r['op'] == 1 and r['rc'] == 0]
    result = dict(label=a.label, kind=a.kind, loops=a.loops, holes=a.holes, variants=a.variants,
        pause_ms=a.pause_ms,external_capture_replay=bool(a.replay_from),
        enabled_trace_events=enabled_events,trace_overruns=trace_overruns,
        gpu_suspend_events=trace_text.count('msm_gpu_suspend:') if trace else None,
        gpu_resume_events=trace_text.count('msm_gpu_resume:') if trace else None,
        debug=a.debug, exit=child.returncode if child else None, error=error,
        before=before, after=counts(), core_saved=len(saved), capture_errors=errors,
        vm_bind_ops=len(rows), successful_maps=len(maps),
        unaligned64k_maps=sum(r['iova'] % 65536 != 0 for r in maps),
        failed_bind_ops=sum(r['rc'] != 0 for r in rows),
        elapsed_seconds=time.monotonic()-start, delayed_observation_seconds=observed,
        boot_preserved=Path('/proc/sys/kernel/random/boot_id').read_bytes() == boot,
        desktop_preserved=desktop() == original_pids,
        taint=Path('/proc/sys/kernel/tainted').read_text().strip(),
        driver_library_sha256=hashlib.sha256(library.read_bytes()).hexdigest())
    (out/'desktop-pids-final-private.json').write_text(json.dumps(desktop()))
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result), flush=True)
    if error or result['exit'] != 0: raise SystemExit(2)
