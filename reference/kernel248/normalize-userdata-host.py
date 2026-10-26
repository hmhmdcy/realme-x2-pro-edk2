"""Remove one verified F2FS library stdout diagnostic, preserving every image byte."""
from pathlib import Path
import hashlib,json,subprocess,time,traceback
P=Path('/mnt/e/edk2-samurai-out/kernel248');work=Path('/home/cy122/x2pro-linux/gnss248-return-validation');work.mkdir(mode=0o700)
cfg=json.loads((P/'userdata-server-config-private.json').read_text());state=json.loads((P/'userdata-worker-state-private.json').read_text())['state'];verified=json.loads((P/'userdata-r6-download-validation-private.json').read_text());prior=json.loads((P/'userdata-host-validation-r6-progress-private.json').read_text())
assert verified['full_sha256_matches_source'] and prior['compressed_sha256_matches_source'] and prior['compressed_sha256']==state['sha256']
source=P/cfg['output_filename'];assert source.stat().st_size==state['bytes_generated']
dest=work/'linux-userdata-clean-r6-private.pcl.zst';assert not dest.exists()
expected=b'[update_superblock: 765] Info: Done to update superblock\n'
report=dict(source_bytes=source.stat().st_size,source_sha256=state['sha256'],source_full_sha_already_verified=True,removed_library_diagnostic_bytes=len(expected),partclone_bytes=0)
def save(phase):
 report['phase']=phase;(P/'userdata-normalization-progress-private.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(phase=phase,partclone_bytes=report['partclone_bytes'])),flush=True)
with (P/'userdata-normalize-zstd-private.log').open('xb') as zd,(P/'userdata-normalize-chkimg-private.log').open('xb') as pc,(P/'userdata-normalize-compress-private.log').open('xb') as zc,dest.open('xb') as target:
 dec=subprocess.Popen(['zstd','-d','-c',str(source)],stdout=subprocess.PIPE,stderr=zd,bufsize=0)
 prefix=bytearray()
 while len(prefix)<len(expected):
  b=dec.stdout.read(len(expected)-len(prefix));assert b;prefix.extend(b)
 assert bytes(prefix)==expected
 check=subprocess.Popen(['partclone.chkimg','-s','-','-L',str(P/'userdata-normalize-chkimg-internal-private.log')],stdin=subprocess.PIPE,stdout=pc,stderr=pc)
 enc=subprocess.Popen(['zstd','-T4','-3','--check','-q','-c'],stdin=subprocess.PIPE,stdout=target,stderr=zc)
 digest=hashlib.sha256();last=0;save('checking_and_normalizing_partclone_framing')
 try:
  while b:=dec.stdout.read(1024**2):
   digest.update(b);check.stdin.write(b);enc.stdin.write(b);report['partclone_bytes']+=len(b)
   if time.monotonic()-last>5:save('checking_and_normalizing_partclone_framing');last=time.monotonic()
  check.stdin.close();enc.stdin.close();dr=dec.wait();cr=check.wait();er=enc.wait();assert dr==cr==er==0,(dr,cr,er)
 finally:
  for child in [dec,check,enc]:
   if child.poll() is None:child.terminate();child.wait(timeout=30)
report.update(source_zstd_exit_code=dr,partclone_chkimg_exit_code=cr,clean_zstd_exit_code=er,partclone_uncompressed_sha256=digest.hexdigest(),clean_path=str(dest),clean_bytes=dest.stat().st_size)
digest=hashlib.sha256()
with dest.open('rb') as f:
 while b:=f.read(8*1024**2):digest.update(b)
report['clean_sha256']=digest.hexdigest();save('complete');(P/'userdata-normalization-validation-private.json').write_text(json.dumps(report,indent=2)+'\n')
