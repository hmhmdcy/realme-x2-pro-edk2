from pathlib import Path
import json,re,subprocess
assert Path('/proc/sys/kernel/random/boot_id').read_bytes()==Path('/var/lib/samurai/k211-baseline/boot-id-private.txt').read_bytes()
out=Path('/var/lib/samurai/k211-provider-inspection');out.mkdir(mode=0o700)
providers=set()
for p in Path('/usr/lib').glob('libcamera*.so*'):
    if p.is_file():providers|={s.decode() for s in re.findall(rb'/dev/dma_heap/[A-Za-z0-9_,.-]+',p.read_bytes())}
p=subprocess.run(['cam','--list'],capture_output=True,text=True,timeout=30);(out/'cam-list-stdout-private.txt').write_text(p.stdout);(out/'cam-list-stderr-private.txt').write_text(p.stderr)
report=dict(stage=211,libcamera_dma_heap_paths=sorted(providers),cam_list_exit=p.returncode,allocator_open_failure='Could not open any dma-buf provider' in p.stderr,software_isp_create_failure='Failed to create software ISP' in p.stderr,crop_error_still_present='Failed to retrieve the sensor crop rectangle' in p.stderr,libcamera_version=subprocess.check_output(['apk','info','-v','libcamera'],text=True).strip())
(out/'summary.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
