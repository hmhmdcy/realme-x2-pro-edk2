"""Bounded simultaneous GPU work on separate devices and address spaces."""
from pathlib import Path
import json, os, subprocess, sys, time

kind, frames = sys.argv[1], int(sys.argv[2])
assert kind in ['vulkan', 'gles'] and 1 <= frames <= 200
out = Path(os.environ['K148_IOCTL_LOG']).parent
commands = [['/var/lib/samurai/k148-tools/vulkan-pixel-probe', str(frames)]]
if kind == 'vulkan':
    commands.append(commands[0][:])
else:
    commands.append(['gtk4-rendernode-tool', 'benchmark', '--renderer=gl',
                     '--runs='+str(frames), '/var/lib/samurai/k148-tools/gsk-effects.node'])

children, logs = [], []
start = time.monotonic()
try:
    for i, cmd in enumerate(commands):
        f = (out/('parallel-'+str(i)+'-private.log')).open('wb')
        logs.append(f)
        children.append(subprocess.Popen(cmd, stdout=f, stderr=subprocess.STDOUT))
    deadline = start + min(170, max(30, frames*(int(os.environ.get('K148_PAUSE_MS', '0'))/1000+.7)+10))
    while any(p.poll() is None for p in children):
        if any(p.returncode not in [None, 0] for p in children):
            raise RuntimeError('A parallel GPU workload failed')
        if time.monotonic() > deadline:
            raise TimeoutError('Parallel GPU workload exceeded its bound')
        time.sleep(.1)
    assert all(p.returncode == 0 for p in children)
    result = dict(kind=kind, workers=len(children), exit_codes=[p.returncode for p in children],
                  elapsed_seconds=time.monotonic()-start)
    (out/'parallel-result.json').write_text(json.dumps(result, indent=2)+'\n')
    print('PARALLEL_PASS '+json.dumps(result), flush=True)
finally:
    for p in children:
        if p.poll() is None:
            p.terminate()
            try: p.wait(timeout=3)
            except subprocess.TimeoutExpired: p.kill(); p.wait()
    for f in logs: f.close()
