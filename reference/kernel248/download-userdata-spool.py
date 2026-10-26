"""Fetch a complete RAM image in SHA-checked ranges; never trust curl exit alone."""
from pathlib import Path
import hashlib,json,shutil,subprocess,time
P=Path('/mnt/e/edk2-samurai-out/kernel248')
cfg=json.loads((P/'userdata-server-config-private.json').read_text());s=json.loads((P/'userdata-worker-state-private.json').read_text())['state']
assert s['state']=='complete' and s['partclone_exit_code']==s['zstd_exit_code']==0
dest=P/cfg['output_filename'];assert not dest.exists() and dest.parent==P
old=P/'linux-userdata-partclone-r5-private.zst'

def sha(path):
 digest=hashlib.sha256()
 with path.open('rb') as f:
  while b:=f.read(8*1024**2):digest.update(b)
 return digest.hexdigest()

reuse=old.stat().st_size==s['prefix_bytes'] and sha(old)==s['prefix_sha256']
if reuse:shutil.copyfile(old,dest)
else:
 with dest.open('xb'):pass
progress=dict(prefix_reused_after_exact_sha_check=reuse,received_bytes=dest.stat().st_size,total_bytes=s['bytes_generated'],verified_range_count=0)
url=f"http://{cfg['bind_address']}:{cfg['port']}/{cfg['token']}/userdata.pcl.zst"
def win(p):return 'E:/edk2-samurai-out/kernel248/'+p.name
while dest.stat().st_size<s['bytes_generated']:
 start=dest.stat().st_size;end=min(start+16*1024**2,s['bytes_generated'])-1;ok=False
 for attempt in range(4):
  chunk=P/f'userdata-r6-range-{start}-{attempt}-private.part';header=chunk.with_suffix('.headers');assert not chunk.exists()
  r=subprocess.run(['/mnt/c/Windows/System32/curl.exe','--disable','--noproxy','*','--fail','--silent','--show-error','--range',f'{start}-{end}','--dump-header',win(header),'--connect-timeout','10','--max-time','45','--speed-time','15','--speed-limit','1024','--output',win(chunk),url],capture_output=True,timeout=50)
  (chunk.with_suffix('.log')).write_bytes(r.stdout+r.stderr)
  headers=header.read_text(errors='replace') if header.exists() else ''
  entries={l.split(':',1)[0].lower():l.split(':',1)[1].strip() for l in headers.splitlines() if ':' in l}
  if r.returncode==0 and chunk.exists() and chunk.stat().st_size==end-start+1 and entries.get('content-range')==f"bytes {start}-{end}/{s['bytes_generated']}" and sha(chunk)==entries.get('x-chunk-sha256'):
   with dest.open('ab') as output,chunk.open('rb') as source:shutil.copyfileobj(source,output)
   chunk.unlink();ok=True;break
 assert ok,'Range could not be verified; keep partial destination and complete RAM source'
 progress.update(received_bytes=dest.stat().st_size,verified_range_count=progress['verified_range_count']+1)
 (P/'userdata-r6-download-progress-private.json').write_text(json.dumps(progress,indent=2)+'\n')
 print(json.dumps(progress),flush=True)
assert sha(dest)==s['sha256'];progress['full_sha256_matches_source']=True
(P/'userdata-r6-download-validation-private.json').write_text(json.dumps(progress,indent=2)+'\n');print('Complete compressed image verified against RAM source',flush=True)
