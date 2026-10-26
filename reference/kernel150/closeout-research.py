"""Retain the evidence and verify the unchanged installed system."""
from pathlib import Path
import hashlib, json, os, re, subprocess, tarfile

os.umask(0o077)
base = Path('/var/lib/samurai/k150-research')
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(Path('/usr/lib/libvulkan_freedreno.so')) == '97f3638851b534070f649fabfbdbb3d330b4ad0e2b0ea93b78026ad71d78fb5e'
assert digest(Path('/var/lib/samurai/k149-deployment/libvulkan_freedreno.so.original')) == 'c72f5ee34e9f4fcf200e4987285f6fdfef4442fd146b77a4c0d1cbf5d5525955'
assert Path('/proc/sys/kernel/random/boot_id').read_bytes() == (base/'boot-id-private.txt').read_bytes()
text = subprocess.check_output(['dmesg'], text=True)
counts = {k: text.count(v) for k, v in dict(gpu_faults='gpu fault:', warnings='WARNING:',
    dpu_timeouts='frame done timeout', dsi_errors='dsi_err_worker',
    dma_prepare='unable to prepare channel').items()}
assert counts == dict(gpu_faults=3, warnings=0, dpu_timeouts=0, dsi_errors=0, dma_prepare=0)
physical = {}
for name in ['phoc', 'phosh']:
    found = subprocess.run(['pgrep', '-x', name], capture_output=True, text=True)
    present = False
    for pid in found.stdout.split():
        try:
            s = (Path('/proc')/pid/'status').read_text()
            present |= int(re.search(r'^Uid:\s+(\d+)', s, re.M)[1]) == 10000
        except FileNotFoundError:
            pass
    physical[name] = present
assert all(physical.values())
active = 0
for entry in Path('/proc').glob('[0-9]*'):
    try:
        executable = (entry/'cmdline').read_bytes().split(b'\0')[0]
        active += executable in [str(base/'suballocation-probe').encode(),
            str(base/'vulkan-capabilities').encode(), b'/var/lib/samurai/k149-tools/vulkan-hole-probe']
    except (FileNotFoundError, PermissionError):
        pass
assert active == 0
assert Path('/proc/sys/kernel/tainted').read_text().strip() == '0'
assert not list(Path('/sys/class/devcoredump').glob('devcd*'))
first = json.loads((base/'result.json').read_text())
second = json.loads((base/'suballocation-result.json').read_text())
summary = dict(research_only=True, kernel_compatibility_candidate_deployed=False,
    current_system='kernel147/software132 with existing Mesa149 library',
    same_boot_verified=True, physical_desktop_present=physical,
    system_library_sha256=digest(Path('/usr/lib/libvulkan_freedreno.so')),
    original_tested_library_sha256=first['stock_library_sha256'],
    active_test_processes=active, pending_devcoredumps=0, taint=0, counts=counts,
    total_pixel_iterations=first['tests'][-1]['pixel_result_lines']+sum(t['pixel_rows'] for t in second['tests']),
    total_pixels=first['tests'][-1]['pixels_verified']+second['total_pixels'],
    total_mismatches=first['tests'][-1]['pixel_mismatches']+sum(t['pixel_mismatches'] for t in second['tests']),
    prefix_bytes_checked=second['total_prefix_bytes'], new_gpu_faults=0)
(base/'closeout.json').write_text(json.dumps(summary, indent=2)+'\n')
manifest = {str(p.relative_to(base)): digest(p) for p in base.rglob('*') if p.is_file()}
(base/'manifest-private.json').write_text(json.dumps(manifest, indent=2)+'\n')
archive = base.parent/'k150-research-private.tar.gz'
with tarfile.open(archive, 'w:gz') as tar: tar.add(base, arcname=base.name)
summary['evidence_archive_sha256'] = digest(archive)
summary['evidence_archive_bytes'] = archive.stat().st_size
(base/'closeout-export.json').write_text(json.dumps(summary, indent=2)+'\n')
print(json.dumps(summary))
