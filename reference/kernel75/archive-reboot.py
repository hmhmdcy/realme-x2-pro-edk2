from pathlib import Path
import gzip, hashlib, json, re, shutil

ref=Path(__file__).resolve().parent
out=Path('/mnt/e/edk2-samurai-out/kernel75')
sha=lambda data:hashlib.sha256(data).hexdigest()
captures=json.loads((ref/'capture-validation.json').read_text())
for n in ('reboot-first-dmesg','reboot-complete-dmesg','reboot-tests',
          'gpu-boot-dmesg','failed-final','reboot-blocked-dmesg'):
    p=out/(n+'.gz')
    if not p.exists():continue
    compressed=p.read_bytes()
    raw=gzip.decompress(compressed)
    captures[n]=dict(raw_bytes=len(raw),raw_sha256=sha(raw),
                     gzip_bytes=len(compressed),gzip_sha256=sha(compressed))
    shutil.copyfile(p,ref/p.name)
    if n.startswith('reboot-'):(ref/(n+'.txt')).write_bytes(raw)
s=(ref/'reboot-complete-dmesg.txt').read_text()
assert not re.search(r'dsi_err_worker|Unhandled context fault|Unable to handle kernel|\b(?:BUG:|Oops:)|vblank.*timed out',s,re.I)
assert sha(s.encode())=='3d9b758f5c7fe3a2c2b4bebe588a8a4ff54a02a6160d63b9d09ad3fb3759a9b0'
tests=(ref/'reboot-tests.txt').read_text()
assert sha(tests.encode())=='6cd82ad7ff07fe95045177b74c9f61faf34588ad54e3d88061079a03635d8ab6'
assert 'af922f36-bacd-481d-a5c5-21c8e3fada65' in tests
assert tests.count('Native panel disable/unprepare and prepare/enable cycle passed')==3
assert tests.count('scanout CRC')==24
assert 'PASS real A640 vertex/fragment rasterization: 12 submissions' in tests
assert tests.rstrip().endswith('TAINT\n0')
report=json.loads((ref/'evidence-validation.json').read_text())
report.update(second_boot_verified=True,second_boot_id='af922f36-bacd-481d-a5c5-21c8e3fada65',
              second_boot_gpu_submissions=12,second_boot_panel_power_cycles=3,
              second_boot_dsi_errors=0,second_boot_taint=0,total_gpu_submissions=39096,
              final_build_regression_panel_cycles=12)
(ref/'evidence-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
(ref/'capture-validation.json').write_text(json.dumps(captures,indent=2)+'\n')
for n in ('final-reboot-reboot.json','emergency-restart-receipt.txt',
          '0011-drm-msm-sm8150-stalled-boot-and-gpu.patch.checkpatch.txt',
          '0012-drm-dsi-sofef03f-stock-clock-and-eot.patch.checkpatch.txt'):
    if (out/n).exists():shutil.copyfile(out/n,ref/n)
p=ref/'display-failure.md'
text=p.read_text().replace('`a4543a18-48bb-488c-b3da-139a6957a004`-48bb-488c-b3da-139a6957a004',
                          '`a4543a18-48bb-488c-b3da-139a6957a004`')
text+='''
The same final #76 image was rebooted again without a flash. Boot ID
`af922f36-bacd-481d-a5c5-21c8e3fada65` passes twelve additional GPU draws and
three panel power cycles, with zero DSI worker errors in the complete log.
Total verified GPU draws are 39,096; final-build regression panel cycles are
twelve. The second boot adds automated evidence, not a second optical report.
'''
p.write_text(text)
print('Second boot validated; total GPU draws=39096, final-build panel regression cycles=12.')
