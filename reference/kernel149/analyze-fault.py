"""Correlate the reproduced fault with successful VM_BIND operations."""
from pathlib import Path
import hashlib, json, os, re, runpy, subprocess, tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel149')
out=Path('/mnt/e/edk2-samurai-out/kernel149')
archive=out/'baseline-holes-private.tar.gz'
with tarfile.open(archive) as t:
    data={m.name.removeprefix('./'):t.extractfile(m).read() for m in t if m.isfile()}
name=next(n for n in data if n.endswith('-private.data'))
raw=data[name].decode()
fault=int(re.search(r'iova=([a-fA-F0-9]+)',raw).group(1),16)
rows=[json.loads(line) for line in data['vm-bind-private.jsonl'].decode().splitlines()]
active={}
for r in rows:
    assert r['rc']==0
    if r['op']==1: active[r['iova']]=r
    elif r['op']==0: active.pop(r['iova'],None)
inside=[r for r in active.values() if r['iova']<=fault<r['iova']+r['range']]
nearest=min((r for r in active.values() if r['iova']>fault),key=lambda r:r['iova'])
prior=[r for r in rows if r['op']==1 and r['iova']<=fault<r['iova']+r['range']]
assert not inside and nearest['iova']-fault==8192
assert prior and any(r['op']==0 and r['iova']==prior[-1]['iova'] for r in rows)
assert re.search(r'ptes: .+ 0000000000000000$',raw,re.M)
report=dict(full_core_saved=True,core_bytes=len(data[name]),
    core_sha256=hashlib.sha256(data[name]).hexdigest(),fault_source='CCU',
    fault_direction='READ',fault_type='TRANSLATION',fault_pte_zero=True,
    fault_inside_successful_active_mapping=False,
    fault_precedes_nearest_color_mapping_bytes=nearest['iova']-fault,
    nearest_mapping_size=nearest['range'],nearest_mapping_base_64k_aligned=nearest['iova']%65536==0,
    fault_equals_color_base_rounded_down_64k=fault==nearest['iova']//65536*65536,
    hole_was_explicitly_unmapped=True,all_bind_operations_successful=True,
    baseline_pixel_rows=0,baseline_exit=2)
(out/'fault-mapping-private.json').write_text(json.dumps(dict(fault=fault,nearest=nearest,prior=prior),indent=2)+'\n')
runpy.run_path(str(ref.parent/'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
env=dict(os.environ,RNN_PATH=str(mesa/'mesa-26.2.4/src/freedreno/registers'))
core=out/name;core.write_bytes(data[name])
with (out/'core-decoded-private.txt').open('wb') as f:
    subprocess.run([str(mesa/'decode-build/src/freedreno/decode/crashdec'),'-s','-f',str(core)],
        env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=90)
rd_names=[n for n in data if '/tu_' in n and n.endswith('.rd.gz')]
assert rd_names
rd=out/'baseline-command-private.rd.gz';rd.write_bytes(data[rd_names[0]])
with (out/'baseline-command-private.txt').open('wb') as f:
    subprocess.run([str(mesa/'decode-build/src/freedreno/decode/cffdump'),'--once','--end=1',str(rd)],
        env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=90)
decoded=(out/'baseline-command-private.txt').read_text(errors='replace')
assert 'RB_RESOLVE_SYSTEM_FLAG_BUFFER_BASE: 0x%x'%nearest['iova'] in decoded
report.update(core_decoded=True,first_command_frame_decoded=True,
              color_flag_address_matches_active_mapping=True,
              bin_render_start=decoded.count('RM6_BIN_RENDER_START'),
              bin_resolve=decoded.count('RM6_BIN_RESOLVE'))
(ref/'fault-analysis.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
