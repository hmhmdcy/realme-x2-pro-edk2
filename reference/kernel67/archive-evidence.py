"""Archive closed, log-only captures. Does not access the phone or repair bytes."""
from pathlib import Path
import base64, gzip, hashlib, json, re, shutil

src = Path('/mnt/e/edk2-samurai-out/kernel67')
dst = Path('/mnt/e/RealmeX2Pro edk2/reference/kernel67')
dst.mkdir(exist_ok=True)
for capture in ('before', 'opp', 'usb', 'usb-read'):
    events = [json.loads(x) for x in (src/(capture+'.events.jsonl')).read_text().splitlines()]
    assert events[-1]['event']=='closed' and not events[-1]['worker_alive']
    for suffix in ('.raw', '.txt', '.events.jsonl', '.usbmon'):
        data=(src/(capture+suffix)).read_bytes()
        (dst/(capture+suffix+'.gz')).write_bytes(gzip.compress(data, mtime=0))
    shutil.copy2(src/(capture+'.json'), dst)
for capture in ('opp-f1','usb-f1'):
    for suffix in ('.raw','.txt','.events.jsonl','.usbmon'):
        (dst/(capture+suffix+'.gz')).write_bytes(gzip.compress((src/(capture+suffix)).read_bytes(),mtime=0))
    shutil.copy2(src/(capture+'.json'),dst)
for file in src.iterdir():
    if file.suffix in ('.sh','.ps1') or file.name.endswith(('-hashes.txt','-build.log','-olddefconfig.log','-com-up.txt','-validation.json')) or file.name in ('source-audit.json','opp-finish-state.json','finish-state.json','usb-config.diff','mirror-before.diff','opp.patch','extract-export.py','usb-source-audit.json','boot-loader-excerpt.c','source-audit.py','archive-evidence.py','finish-plan.txt') or '-confirm-' in file.name or '-flash.' in file.name or '-reboot.' in file.name:
        shutil.copy2(file,dst/file.name)
for file in src.glob('*.validated.txt'):
    shutil.copy2(file,dst/file.name)
for file in src.glob('*-received.gz'):
    shutil.copy2(file,dst/file.name)
for name in ('samurai-before.dts','samurai-after.dts','samurai-mirror-before.dts','sm8150-xiaomi-nabu-pinned.dts'):
    shutil.copy2(src/name,dst/name)
for name in ('config-usb-before','config-usb-after'):
    (dst/(name+'.gz')).write_bytes(gzip.compress((src/name).read_bytes(),mtime=0))
text=(src/'opp.txt').read_bytes().decode('ascii').replace('\r','')
start=re.search(r'(?m)^K67OGB$',text)
end=re.search(r'(?m)^K67OGE$',text[start.end():])
section=text[start.end():start.end()+end.start()].strip()+'\n'
(dst/'opp-dmesg-first-export.txt').write_text(section)
lines=section.splitlines()
encoded=''.join(lines[1:])
try:
    base64.b64decode(encoded,validate=True)
except Exception as error:
    bad=dict(device_sha256=lines[0].split()[0],base64_chars=len(encoded),expected_base64_chars=16304,error=str(error),validated=False,no_filling=True)
else:
    raise AssertionError('Initial export unexpectedly valid')
(dst/'opp-dmesg-first-failed.json').write_text(json.dumps(bad,indent=2)+'\n')
# The first live-DT export lost its start marker; the exact capture remains intact.
(dst/'opp-live-dt-first-failed.json').write_text(json.dumps(dict(marker='K67ODB',start_marker_present=bool(re.search(r'(?m)^K67ODB$',text)),validated=False,no_filling=True),indent=2)+'\n')
text=(src/'usb-read.txt').read_bytes().decode('ascii').replace('\r','')
start=re.search(r'(?m)^K67UGB$',text)
end=re.search(r'(?m)^K67UGE$',text[start.end():])
section=text[start.end():start.end()+end.start()].strip()+'\n'
(dst/'usb-dmesg-first-export.txt').write_text(section)
lines=section.splitlines()
data=base64.b64decode(''.join(lines[1:]),validate=True)
digest=sha256_digest=hashlib.sha256(data).hexdigest()
expected=lines[0].split()[0]
assert digest!=expected and len(data)==12609
(dst/'usb-dmesg-first-received.gz').write_bytes(data)
try:
    gzip.decompress(data)
except Exception as error:
    crc_error=str(error)
else:
    raise AssertionError('Initial USB log export unexpectedly passes gzip CRC')
(dst/'usb-dmesg-first-failed.json').write_text(json.dumps(dict(device_sha256=expected,received_sha256=digest,received_bytes=len(data),device_bytes=12618,gzip_error=crc_error,validated=False,no_filling=True),indent=2)+'\n')
print('Closed captures and unchanged failed exports archived:',dst)
