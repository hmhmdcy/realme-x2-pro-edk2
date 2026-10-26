"""Inspect additional init scripts from the already reconstructed ROM, offline."""
from pathlib import Path
import hashlib,json,re,subprocess
R=Path(__file__).resolve().parent;P=Path('/mnt/e/edk2-samurai-out/kernel243');P.mkdir(mode=0o700,exist_ok=True)
O=P/'rom-init';assert not O.exists();O.mkdir(mode=0o700)
images=Path('/mnt/e/edk2-samurai-out/kernel242/android-rom')
sources={}
for part,path in [('vendor','/etc/init'),('vendor','/bin'),('odm','/etc/init'),('system','/system/etc/init')]:
 dest=O/(part+path.replace('/','_'));dest.mkdir(mode=0o700)
 # rdump copies files to a private directory; nothing is executed.
 x=subprocess.run(['debugfs','-R',f'rdump {path} {dest}',str(images/(part+'.img'))],capture_output=True)
 (O/(dest.name+'-debugfs-private.log')).write_bytes(x.stdout+x.stderr)
 assert x.returncode==0
 for p in dest.rglob('*'):
  if not p.is_file() or p.is_symlink() or p.stat().st_size>2*1024*1024:continue
  if p.suffix not in ['.rc','.sh','.conf']:continue
  b=p.read_bytes();s=b.decode(errors='replace');matches=[]
  for i,line in enumerate(s.splitlines()):
   if re.search(r'gnss|gps|lna|modem|mcfg|rmt_storage|qrtr|remoteproc|rf[_-]|rfclk|xo[_-]|clock.*vote|pil[_-]',line,re.I):
    matches.append(dict(line=i+1,text=line))
  if matches:sources[str(p.relative_to(O))]=dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest(),matches=matches)
(P/'rom-init-matches-private.json').write_text(json.dumps(sources,indent=2)+'\n')
report=dict(stage=243,matched_text_files=len(sources),matched_lines=sum(len(v['matches']) for v in sources.values()),offline_only=True,no_vendor_code_executed=True)
(R/'rom-init-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
