from pathlib import Path
import base64,gzip,hashlib,json,re,shutil

src=Path('/mnt/e/edk2-samurai-out/kernel68')
dst=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel68')
dst.mkdir(exist_ok=False)
for name in ('baseline','baseline-read','opp','opp-read','opp-f1'):
    events=[json.loads(s) for s in (src/(name+'.events.jsonl')).read_text().splitlines()]
    if name!='opp-f1':
        assert events[-1]['event']=='closed' and not events[-1]['worker_alive'] and not events[-1]['errors']
    for suffix in ('.raw','.txt','.events.jsonl','.usbmon'):
        (dst/(name+suffix+'.gz')).write_bytes(gzip.compress((src/(name+suffix)).read_bytes(),mtime=0))
    shutil.copy2(src/(name+'.json'),dst)
observations={
 'opp-win-log':dict(acked=68,retries=0,frames=4920,exit=0),
 'opp-win-facts-save':dict(acked=111,retries=0,frames=1048,exit=0),
 'opp-win-dt-save':dict(acked=0,retries=0,frames=0,exit=1,startup_receipt_absent=True,data_sent=False),
 'opp-win-dt-read':dict(acked=138,retries=1,frames=378,exit=0),
 'opp-win-facts':dict(acked=68,retries=1,frames=333,exit=0),
}
for name in observations:
    for suffix in ('.raw','.txt','.events.txt'):
        (dst/(name+suffix+'.gz')).write_bytes(gzip.compress((src/(name+suffix)).read_bytes(),mtime=0))
(dst/'windows-close-observations.json').write_text(json.dumps(dict(source='Closing stdout/stderr observed in exec tool results; independent final process/PnP audit in finish-state.json',captures=observations),indent=2)+'\n')
for f in src.iterdir():
    if f.suffix in ('.sh','.ps1','.py') or f.name.endswith(('-hashes.txt','-validation.json','.validated.txt','-received.gz')) or f.name in ('firmware-build.log','core-sources-before.sha256','build-audit.json','runtime-log-analysis.json','finish-state.json') or f.suffix in ('.out','.err'):
        shutil.copy2(f,dst/f.name)
for name in ('firmware-before.dtb','firmware-after.dtb'):
    (dst/(name+'.gz')).write_bytes(gzip.compress((src/name).read_bytes(),mtime=0))
text=(src/'opp.txt').read_text().replace('\r','')
start=re.search(r'(?m)^K68LGB$',text);end=re.search(r'(?m)^K68LGE$',text[start.end():])
section=text[start.end():start.end()+end.start()].strip()+'\n'
lines=section.splitlines();bad=base64.b64decode(''.join(lines[1:]),validate=True)
expected=lines[0].split()[0];got=hashlib.sha256(bad).hexdigest()
assert got!=expected and len(bad)==12371
try:
    gzip.decompress(bad)
except Exception as e:
    error=str(e)
else:
    raise AssertionError('Damaged first log unexpectedly passes gzip CRC')
(dst/'opp-dmesg-first-export.txt').write_text(section)
(dst/'opp-dmesg-first-received.gz').write_bytes(bad)
(dst/'opp-dmesg-first-failed.json').write_text(json.dumps(dict(validated=False,no_filling=True,device_sha256=expected,received_sha256=got,received_bytes=len(bad),device_bytes=12377,gzip_error=error),indent=2)+'\n')
preserved={
 '/home/cy122/x2pro-linux/linux/drivers/tty/serial/eud.c':'39e464f85b0450a394342b1664a306b2b27caa466b459ef038de2e0ccf6d2ef4',
 '/home/cy122/x2pro-linux/linux/drivers/tty/serial/eud_earlycon.c':'34da9936de5de9b36f232be3b8e0a730f9a56a77a6121b283b8e551bb3c65ad9',
 '/home/cy122/x2pro-linux/initramfs/init':'e9c7c2da0f93509565a36c182b3b39d928ddcba0317ee9d76469317e6b9135ab',
 '/home/cy122/x2pro-linux/linux/arch/arm64/boot/Image':'d51d1260091d0d568c30b6dc6e673474658259654d63b0e65d5f3baf036145ff',
 '/home/cy122/x2pro-linux/linux/.config':'439398137656726f4d2abe57011b9e1c42eb21dbc7f1095ddebec2cf23443546',
}
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in preserved.items())
(dst/'source-preservation.json').write_text(json.dumps(preserved,indent=2)+'\n')
print('Archived closed captures, validated exports, failed exports, and firmware audit. Large firmware/boot images stay in external kernel68 directory.')
