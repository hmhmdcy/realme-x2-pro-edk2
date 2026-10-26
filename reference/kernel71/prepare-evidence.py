from pathlib import Path
import gzip, hashlib, json, re
r=Path('/mnt/e/edk2-samurai-out/kernel71');w=Path('/mnt/e/RealmeX2Pro edk2')
observed={
 'mode-receipt':(0,'K71F'), 'baseline-save':(0,'K71BS'),'baseline-read':(0,'K71BRE'),
 'touch-f1':(0,None),'touch-save':(1,None),'boot-passive':(0,None),
 'touch-save-ready':(0,'K71LS'),'touch-log-read':(0,'K71LRE'),
 'touch-facts-save':(0,'K71TS'),'touch-facts-read':(0,'K71TRE'),
 'touch-event-start':(0,'K71TC'),'touch-event-save':(0,'K71ES'),
 'touch-events-read':(0,'K71MRE'),'finish-save':(0,'K71ZS'),'finish-read':(0,'K71FRE')}
(r/'close-observations.json').write_text(json.dumps(dict(
 source='Close/Dispose and exit codes directly observed in tool stdout/stderr; event logs are verified separately.',
 windows={n:dict(exit_code=c,close_observed=True,end_marker=m) for n,(c,m) in observed.items()},
 wsl=dict(name='touch-f1-wsl',exit_code=1,receipt='F1',read_error='EIO after receipt',
          resources_disposed_observed=True,usbmon_thread_alive=False,finally_detach_attempted=True,
          target_already_disconnected=True,persistent_shell_exited=True)),indent=2)+'\n')
old=json.loads((w/'reference/kernel69/source-preservation.json').read_text())
preserved={p:h for p,h in old.items() if not p.endswith(('/Image','/.config'))}
repo=Path('/home/cy122/edk2-samurai/repo')
for line in (r/'core-sources-before.sha256').read_text().splitlines():
 h,p=line.split(maxsplit=1);preserved[str(repo/p)]=h
for i,(p,h) in enumerate(preserved.items()):
 data=Path(p).read_bytes();assert hashlib.sha256(data).hexdigest()==h,p
 (r/f'preserved-source-{i}.gz').write_bytes(gzip.compress(data,mtime=0))
(r/'source-preservation.json').write_text(json.dumps(preserved,indent=2)+'\n')
# Make archived DT/input analysis independent of the supplemental kernel68 directory.
prefix=Path('/mnt/e/edk2-samurai-out/kernel68/verify-firmware.py').read_text()
func=prefix[prefix.index('def fdt_nodes('):prefix.index('before_dt=')]
p=r/'validate-dtb.py';s=p.read_text();start=s.index('ns={}');end=s.index('a=parse(',start)
s=s[:start]+'align=lambda n,a:(n+a-1)//a*a\n'+func+'parse=fdt_nodes\n'+s[end:]
s=s.replace("root=Path('/mnt/e/edk2-samurai-out/kernel71')","root=Path(__file__).resolve().parent")
p.write_text(s)
p=r/'analyze-input.py';s=p.read_text().replace("r=Path('/mnt/e/edk2-samurai-out/kernel71')","r=Path(__file__).resolve().parent")
s=s.replace("data=(r/'touch-events.validated.txt').read_bytes()","data=(r/'input-events.bin').read_bytes()")
p.write_text(s)
print('Observed closures and immutable source hashes saved; archived DT/input checks made standalone.')
