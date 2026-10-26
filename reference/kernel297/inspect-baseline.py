"""Preserve actual pre-change source and quantify the late-start counter mismatch."""
from pathlib import Path
import hashlib, json, re, subprocess
import host
HERE = Path(__file__).resolve().parent
TREE = Path('/home/cy122/x2pro-linux/camera279-isp-kernel')
git = lambda *a: subprocess.check_output(['git', '-C', str(TREE), *a], text=True).strip()
assert git('rev-parse', 'HEAD') == 'f86906688666c0ebaabaeeec96c28d5741257f50'
assert not git('status', '--porcelain')
baseline = host.PRIVATE / 'source-before297'
assert not baseline.exists()
baseline.mkdir()
sources = {}
for name in ['camss-vfe.c', 'camss-vfe-17x.c']:
    b = (TREE / 'drivers/media/platform/qcom/camss' / name).read_bytes()
    (baseline / name).write_bytes(b)
    sources[name] = hashlib.sha256(b).hexdigest()
capture = json.loads((HERE.parent / 'kernel296/stats-capture-validation.json').read_text())
images, stats = [], []
for line in capture['tool_output'].splitlines():
    if line.startswith(('FRAME number=', 'STATS frame=')):
        row = {k: int(v) for k, v in re.findall(r'\b(number|frame|sequence|timestamp_us)=(\d+)', line)}
        (images if line.startswith('FRAME') else stats).append(row)
rows = []
for s in stats:
    if s['frame'] < 90:
        continue
    nearest = min((i for i in images if i['number'] >= 90), key=lambda i: abs(i['timestamp_us'] - s['timestamp_us']))
    rows.append(dict(stats=s, nearest_image_completion=nearest,
                     time_distance_us=abs(nearest['timestamp_us'] - s['timestamp_us'])))
report = dict(stage=297, baseline_source=git('rev-parse', 'HEAD'), source_sha256=sources,
              late_statistics_completion_comparison=rows,
              completion_proximity_is_not_sof_proof=True,
              source_defect='PIX image/statistics increment independent completion counters; only output[0] receives SOF tags; late metadata copies completed-image count')
(HERE / 'baseline-validation.json').write_text(json.dumps(report, indent=2) + '\n')
code = r'''
from pathlib import Path
import json,os,re,subprocess
assert os.uname().release=='7.3.0-rc6-rmx1931-samurai-k296+' and os.uname().version.startswith('#296 ')
sensors={}
for name in ['s5kgw1','imx471','imx319','s5k3m5','lc898219xi']:
 p=next(p for p in Path('/sys/bus/i2c/drivers',name).glob('*') if p.is_symlink() and re.fullmatch(r'\d+-[0-9a-f]{4}',p.name));sensors[name]=dict(device=p.name,state=(p/'power/runtime_status').read_text().strip())
assert all(s['state']=='suspended' for s in sensors.values())
kernel=subprocess.check_output(['dmesg']);faults={k:kernel.count(v) for k,v in dict(warning=b'WARNING:',oops=b'Oops:',gpu=b'gpu fault:',dsp=b'fatal error received').items()}
assert not any(faults.values()) and Path('/proc/sys/kernel/tainted').read_text().strip()=='0'
print(json.dumps(dict(stage=297,kernel_build=296,release=os.uname().release,sensors=sensors,faults=faults,taint=0,pstore_files=len(list(Path('/sys/fs/pstore').glob('*'))))))
'''
q = host.ssh('python3 -', input=code.encode(), timeout=25)
(host.PRIVATE / 'runtime-preflight-private.json').write_bytes(q.stdout)
(HERE / 'runtime-preflight-validation.json').write_bytes(q.stdout)
print(json.dumps(dict(source_clean=True, late_comparisons=len(rows), first_late=rows[0], runtime=json.loads(q.stdout)), indent=2))
