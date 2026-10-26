"""Cross-check real control writes and constant-EV image transitions before allowing AE."""
from pathlib import Path
import hashlib, json, math, re, shlex, statistics, sys
import host
HERE = Path(__file__).resolve().parent
run = sys.argv[1]
assert re.fullmatch(r'r[1-9][0-9]*', run)
poll = json.loads((host.PRIVATE / f'joint-{run}-poll-private.json').read_text())
assert poll['state']['terminal'] and not poll['matching_worker_live'] and not poll['matching_child_live']
assert poll['summary']['passed']
root = '/var/lib/samurai/k306-joint-' + run
raw = host.ssh('cat ' + shlex.quote(root + '/capture-private.log'), timeout=20).stdout
(host.PRIVATE / f'joint-{run}-capture-private.log').write_bytes(raw)
text = raw.decode(errors='replace')
contexts = {(int(e), int(s)): (int(v), int(x), int(g), int(c)) for e, s, v, x, g, c in
 re.findall(r'SensorContext epoch=(\d+) sof=(\d+) valid=(\d+) exposure-lines=(\d+) gain-code=(\d+) source=(\d+)', text)}
metadata = {(int(e)+1, int(r)): (int(x), float(g)) for e, r, x, g in
 re.findall(r'APPLICATION_SENSOR_METADATA epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)', text)}
luma = {(int(e)+1, int(r)): list(map(float, (a, b, c, d))) for e, r, a, b, c, d in
 re.findall(r'APPLICATION_LUMA epoch=(\d+) request=(\d+) ([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+) ([\d.e+-]+)', text)}
commands = [(int(e)+1, int(r), int(x), float(g)) for e, r, x, g in
 re.findall(r'APPLICATION_SENSOR_COMMAND epoch=(\d+) request=(\d+) exposure_us=(\d+) analogue_gain=([\d.e+-]+)', text)]
pairs = [(int(e), int(s), int(r), int(p), float(m), int(a)) for e, s, r, p, m, a in
 re.findall(r'Pair epoch=(\d+) sof=(\d+) request=(\d+) population=(\d+) mean=([\d.e+-]+) parameters-acknowledged=(\d+)', text)]
assert len(pairs) == len(metadata) == len(luma) == 480 and len(commands) == 18
assert len({(e, s) for e, s, *_ in pairs}) == 480
lineUs = 9648 * 1000000 / 481930000
rounded = lambda n: math.floor(n + .5)
sources = {(e, 0xffffffff): (rounded(20000 / lineUs), 256) for e in [1, 2]}
for e, r, x, g in commands:
    assert (x, g) == ((10000, 16.0) if r // 24 % 2 else (20000, 8.0))
    sources[e, r] = (rounded(x / lineUs), rounded(32 * g))
actual, domains = {}, {}
for e, s, r, p, m, a in pairs:
    v, x, g, c = contexts[e, s]
    assert v and p == 820560 and a == 1 and (x, g) == sources[e, c]
    assert metadata[e, r][0] == rounded(x * lineUs) and abs(metadata[e, r][1] - g / 32) < .00001
    actual[e, s] = (x, g, c)
    domains[e, s] = [m] + luma[e, r]
changes = []
for e in [1, 2]:
    for s in range(1, 240):
        if actual[e, s][2] != actual[e, s-1][2]:
            checks = []
            for d in range(5):
                before = [domains[e, k][d] for k in range(s-6, s-2)]
                after = [domains[e, k][d] for k in range(s+6, s+14)]
                pre, post = statistics.median(before), statistics.median(after)
                scale = max(pre, post, 1)
                mad = max(statistics.median(abs(v-pre) for v in before), statistics.median(abs(v-post) for v in after))
                stable = min(pre, post) > 4 and abs(pre-post) < .10 * scale and mad < .02 * scale
                tolerance = max(.08 * scale, 8 * mad)
                transient = [domains[e, k][d] for k in range(s-1, s+3)]
                checks.append(dict(scene_stable=stable,
                    no_mixed_ev_transient=stable and all(min(pre,post)-tolerance <= v <= max(pre,post)+tolerance for v in transient)))
            changes.append(dict(epoch=e, effective_sof=s, source_request=actual[e,s][2], domains=checks))
assert len(changes) == 18
trace, current = [], None
for row in text.splitlines():
    m = re.search(r'SOF epoch=(\d+) sequence=(\d+)', row)
    if m: current = (int(m[1]), int(m[2]))
    m = re.search(r'DelayedControls .*Setting (Exposure|Analogue Gain) to (\d+) at index', row)
    if m: assert current is not None; trace.append((*current, m[1], int(m[2])))
expected = []
for change in changes:
    e, s = change['epoch'], change['effective_sof']
    expected += [(e,s-2,'Exposure',actual[e,s][0]), (e,s-2,'Analogue Gain',actual[e,s][1])]
assert len(trace) == 36 and sorted(trace) == sorted(expected)
bundle = json.loads((HERE / 'bundle-joint-validation.json').read_text())
code = 'from pathlib import Path;import hashlib,json;p=Path(' + repr(root + '/bundle') + ');print(json.dumps({n:hashlib.sha256((p/n).read_bytes()).hexdigest() for n in ' + repr(list(bundle['files'])) + '}))'
hashes = json.loads(host.ssh('python3 -c ' + shlex.quote(code), timeout=20).stdout)
assert hashes == {n: entry['sha256'] for n, entry in bundle['files'].items()}
report = dict(stage=306, run=run, actual_kernel_build=298, frames=480, joint_changes=18, real_writes=36,
              exact_effective_sof_context_and_metadata_verified=True, both_writes_at_sof_minus2=True,
              phone_bundle_hashes_verified=True, changes=changes,
              domain_order=['linear_BHIST', 'NV12_Y_quarter1', 'NV12_Y_quarter2', 'NV12_Y_quarter3', 'NV12_Y_quarter4'],
              passed=all(d['no_mixed_ev_transient'] for c in changes for d in c['domains']),
              not_pixelwise_lock_or_dark_calibration=True)
(HERE / 'joint-physical-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['changes','domain_order']}, indent=2))
