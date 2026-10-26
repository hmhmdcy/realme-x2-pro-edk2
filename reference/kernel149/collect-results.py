"""Export statistics without device addresses, identities or process logs."""
from pathlib import Path
import hashlib, json, re
root=Path('/var/lib/samurai')
rows=[]
for out in sorted(root.glob('k149-*')):
    receipt=out/'result.json'
    if not receipt.is_file(): continue
    r=json.loads(receipt.read_text())
    log=(out/'probe-private.log').read_text(errors='replace')
    pixel=re.findall(r'PIXEL iteration=(\d+) size=(\d+)x(\d+) samples=(\d+) format=(\d+) draws=(\d+) mismatches=(\d+)',log)
    r.update(pixel_readbacks=len(pixel),pixels_checked=sum(int(x[1])*int(x[2]) for x in pixel),
             pixel_mismatches=sum(int(x[6]) for x in pixel),
             pixel_iterations_complete=len(pixel)==r['loops'] if r.get('kind','pixel')=='pixel' else None,
             summary_printf_argument_order_bug=r['label']=='candidate-holes',
             receipt_sha256=hashlib.sha256(receipt.read_bytes()).hexdigest())
    if r.get('kind')=='memory':
        sparse=re.findall(r'SPARSE_REMAP iteration=(\d+) bank=(\d+) mismatches=(\d+)',log)
        replay=re.findall(r'CAPTURE_REPLAY iteration=(\d+) external=(\d+) address_64k_aligned=(\d+) mismatches=(\d+)',log)
        r.update(sparse_remaps=len(sparse),capture_replays=len(replay),
                 memory_mismatches=sum(int(x[2]) for x in sparse)+sum(int(x[3]) for x in replay),
                 old_unaligned_capture_replayed=bool(replay) and all(x[1]=='1' and x[2]=='0' for x in replay))
    if (out/'settings-cleanup.json').exists():
        r['application_cleanup']=json.loads((out/'settings-cleanup.json').read_text())
    if (out/'parallel-result.json').exists():
        r['parallel_result']=json.loads((out/'parallel-result.json').read_text())
        child_pixel=re.findall(r'PIXEL iteration=(\d+) size=(\d+)x(\d+) samples=(\d+) format=(\d+) draws=(\d+) mismatches=(\d+)',
            (out/'parallel-0-private.log').read_text(errors='replace'))
        r.update(pixel_readbacks=len(child_pixel),pixels_checked=sum(int(x[1])*int(x[2]) for x in child_pixel),
                 pixel_mismatches=sum(int(x[6]) for x in child_pixel),pixel_iterations_complete=len(child_pixel)==r['loops'])
    if r['label']=='deployed-gmem-hole-formats':
        r['desktop_guard_limit']='Counted a simultaneous isolated test compositor; physical desktop identity is checked in later tests.'
    if r['label']=='deployed-parallel-gles':
        r['harness_failure']='GTK OpenGL could not initialize because the runner omitted WAYLAND_DISPLAY and XDG_RUNTIME_DIR; corrected in the subsequent run.'
    rows.append(r)
print(json.dumps(dict(stage=149,tests=rows),indent=2))
