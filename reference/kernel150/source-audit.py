"""Audit exact released Mesa inputs and summarize existing experiment logs."""
from pathlib import Path
import hashlib, json, re, tarfile

base = Path('/var/lib/samurai/k150-research')
archive = Path('/var/lib/samurai/k148-sdk-apks/mesa-26.2.4.tar.xz')
digest = lambda data: hashlib.sha256(data).hexdigest()
expected = 'bce5f7fbebb934373b86c999a064d52fb5065878dc57f287f95346648ec832e9'
assert digest(archive.read_bytes()) == expected
names = ['src/freedreno/vulkan/tu_knl_drm_msm.cc', 'src/freedreno/vulkan/tu_device.cc',
         'src/freedreno/drm/msm/msm_pipe.c', 'src/gallium/drivers/freedreno/freedreno_screen.c',
         'src/freedreno/vulkan/tu_image.cc', 'src/freedreno/fdl/fd6_layout.c']
sources = {}
with tarfile.open(archive) as package:
    for name in names:
        data = package.extractfile('mesa-26.2.4/'+name).read()
        assert data == (Path('/var/lib/samurai/k148-mesa/mesa-26.2.4')/name).read_bytes()
        sources[name] = dict(sha256=digest(data), live_source_matches_release=True)
    shared = package.extractfile('mesa-26.2.4/src/freedreno/vulkan/tu_knl_drm.cc').read().decode()
    assert shared.count('util_vma_heap_alloc(&dev->vma, size, os_page_size)') == 2
sources['src/freedreno/vulkan/tu_knl_drm.cc'] = dict(
    released_automatic_allocation_alignment='os_page_size', patched_live_file_not_used_by_stock_ICD=True)
report = json.loads((base/'result.json').read_text())
pixel = next(r for r in report['tests'] if r['label'] == 'stock-gmem-holes')
log = (base/'stock-gmem-holes/stdout-private.log').read_text()
rows = re.findall(r'^PIXEL iteration=.*$', log, re.M)
summary = re.search(r'ALL_PIXELS_PASS iterations=(\d+) pixels=(\d+)', log)
assert summary and len(rows) == int(summary[1]) == 18
pixel['pixel_result_lines'] = len(rows)
pixel['pixel_mismatches'] = sum(int(re.search(r'mismatches=(\d+)', s)[1]) for s in rows)
pixel['pixels_verified'] = int(summary[2])
pixel['parser_corrected_from_saved_logs_without_rerun'] = True
assert pixel['pixel_mismatches'] == 0 and pixel['get_iova_calls'] == 183
assert pixel['vm_bind_calls'] == pixel['set_iova_calls'] == pixel['unaligned_get_iova'] == 0
report['source_provenance'] = dict(mesa_version='26.2.4', archive_sha256=expected,
    official_checksum_url='https://docs.mesa3d.org/relnotes/26.2.4.html', sources=sources)
(base/'result.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report))
