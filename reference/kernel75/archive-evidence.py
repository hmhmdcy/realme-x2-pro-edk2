from pathlib import Path
import gzip, hashlib, json, re, shutil

ref = Path(__file__).resolve().parent
out = Path('/mnt/e/edk2-samurai-out/kernel75')
sha = lambda data: hashlib.sha256(data).hexdigest()
names = ['matched-boot-dmesg','mixed-tests','flower-dmesg','static-white-dmesg',
         'dsc-diag-dmesg','dsc-diag-final','no-eot-dmesg','no-eot-final',
         'noncontinuous-dmesg','noncontinuous-complete','final-first-dmesg',
         'final-bars-dmesg','final-complete-dmesg','final-tests']
captures = {}
for n in names:
    source = out/(n+'.gz')
    assert source.exists(), n
    compressed = source.read_bytes()
    raw = gzip.decompress(compressed)
    assert raw, n
    captures[n] = dict(raw_bytes=len(raw),raw_sha256=sha(raw),
                       gzip_bytes=len(compressed),gzip_sha256=sha(compressed))
    shutil.copyfile(source,ref/source.name)
    if n.startswith('final-'):
        (ref/(n+'.txt')).write_bytes(raw)
final = gzip.decompress((out/'final-complete-dmesg.gz').read_bytes()).decode()
assert not re.search(r'dsi_err_worker|Unhandled context fault|Unable to handle kernel|\b(?:BUG:|Oops:)|vblank.*timed out',final,re.I)
tests = gzip.decompress((out/'final-tests.gz').read_bytes()).decode()
draws = [int(n) for n in re.findall(r'PASS real A640 vertex/fragment rasterization: (\d+) submissions',tests)]
assert draws == [3000,12,3000,12,3000,12], draws
assert tests.count('Native panel disable/unprepare and prepare/enable cycle passed') == 9
assert tests.count('scanout CRC') == 72
assert tests.rstrip().endswith('TAINT\n0')
for n in ('final-validation.json','patch-validation.json','final-source-manifest.json',
          'dtb-validation.json','initramfs-validation.json','final-flash-validation.json',
          'candidate-manifest.json','final-device-readback.txt','no-eot-device-readback.txt',
          'final-f1-wsl.events.jsonl','final-reboot-f1-wsl.events.jsonl',
          'no-eot-flash-validation.json','noncontinuous-flash-validation.json',
          'noncontinuous-build-hashes.txt','final-build-hashes.txt'):
    source=out/n
    if source.exists(): shutil.copyfile(source,ref/n)
report = dict(final_boot_id='770389cb-a7fe-4b81-bddd-fec402a1c5b8',build=76,taint=0,
              final_gpu_submissions=sum(draws),earlier_gpu_submissions=30048,
              total_gpu_submissions=sum(draws)+30048,final_panel_power_cycles=9,
              final_crc_pairs=72,final_dsi_errors=0,
              physical_white_confirmed=dict(build=75,boot_id='c66a6b88-f507-402b-a807-f75184e99bd2',
                                             observation='已经全白，没有噪点',after_prior_power_cycle=True),
              physical_first_bars_confirmed=dict(build=76,boot_id='770389cb-a7fe-4b81-bddd-fec402a1c5b8',
                                                 observation='彩条清晰，显示正常',before_recovery_power_cycle=True),
              acceptance_limits=['cold power removal','90Hz','suspend/resume',
                                 'brightness optical calibration','all GPU OPP stress'])
(ref/'capture-validation.json').write_text(json.dumps(captures,indent=2)+'\n')
(ref/'evidence-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
text=(ref/'display-failure.md').read_text().replace('\x074543a18','`a4543a18-48bb-488c-b3da-139a6957a004`')
text=text.replace('-48bb-488c-b3da-139a6957a004-48bb-488c-b3da-139a6957a004','-48bb-488c-b3da-139a6957a004')
text += '''
## Accepted noncontinuous-clock configuration

Build #75 cleared EOT append and the inherited controller/PHY forced-clock
requests. After its first panel power cycle, the user confirmed the white hold
as "已经全白，没有噪点". Its early log still contained 147 DSI worker messages;
those ended at 104.57 s. This is not evidence of a clean first boot.

The final #76 removes only the read-only DSC register diagnostics. On a fresh
boot, before any display recovery cycle, the user confirmed native color bars
as "彩条清晰，显示正常". Complete logs contain zero DSI worker errors, no
unhandled SMMU context fault or kernel Oops, and taint remains zero. Its 9,036
real A640 draws and nine panel power cycles pass. These optical observations
support the deployed configuration; EOT-only was insufficient. We did not
change the measured link rate, supply voltages, DSC PPS or EUD transport.
'''
(ref/'display-failure.md').write_text(text)
print('Archived validated captures; GPU draws',report['total_gpu_submissions'],
      'and physical acceptance recorded separately.')
