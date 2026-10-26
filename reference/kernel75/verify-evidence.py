from pathlib import Path
import gzip, hashlib, json, re

ref=Path(__file__).resolve().parent
sha=lambda data:hashlib.sha256(data).hexdigest()
captures=json.loads((ref/'capture-validation.json').read_text())
for name,item in captures.items():
    compressed=(ref/(name+'.gz')).read_bytes()
    raw=gzip.decompress(compressed)
    assert len(compressed)==item['gzip_bytes'] and sha(compressed)==item['gzip_sha256'],name
    assert len(raw)==item['raw_bytes'] and sha(raw)==item['raw_sha256'],name
    if (ref/(name+'.txt')).exists():assert (ref/(name+'.txt')).read_bytes()==raw,name
for name in ('final-first-dmesg','final-complete-dmesg','reboot-first-dmesg','reboot-complete-dmesg'):
    raw=gzip.decompress((ref/(name+'.gz')).read_bytes()).decode()
    assert not re.search(r'dsi_err_worker|Unhandled context fault|Unable to handle kernel|\b(?:BUG:|Oops:)|vblank.*timed out',raw,re.I),name
report=json.loads((ref/'evidence-validation.json').read_text())
assert report['total_gpu_submissions']==39096 and report['second_boot_verified']
assert report['taint']==report['second_boot_taint']==0
assert report['physical_white_confirmed']['observation']=='已经全白，没有噪点'
assert report['physical_first_bars_confirmed']['observation']=='彩条清晰，显示正常'
assert report['physical_first_bars_confirmed']['before_recovery_power_cycle']
for name,expected,calls in (('final-tests',[3000,12,3000,12,3000,12],9),('reboot-tests',[12],3)):
    text=gzip.decompress((ref/(name+'.gz')).read_bytes()).decode()
    draws=[int(x) for x in re.findall(r'PASS real A640 vertex/fragment rasterization: (\d+) submissions',text)]
    assert draws==expected,name
    assert text.count('Native panel disable/unprepare and prepare/enable cycle passed')==calls,name
    assert text.count('scanout CRC')==calls*8,name
    assert text.rstrip().endswith('TAINT\n0'),name
patches=json.loads((ref/'patch-validation.json').read_text())
for name,item in patches.items():
    assert item['exact_apply_pass'] and item['checkpatch_exit']==0,name
    assert sha((ref.parents[1]/'linux-port/patches'/name).read_bytes())==item['sha256'],name
assert json.loads((ref/'final-validation.json').read_text())['historical_kernel74_seal_pass']
seal=ref/'SHA256SUMS'
if seal.exists():
    for line in seal.read_text().splitlines():
        expected,name=line.split('  ',1)
        assert sha((ref/name).read_bytes())==expected,name
print('PASS:',len(captures),'capture hashes/CRC/lengths; 39096 GPU draws; 12 final-build panel cycles; optical evidence; exact patches and seal.')
