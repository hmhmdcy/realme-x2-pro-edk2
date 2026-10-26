"""Verify normalized image and restore it to an owned PC sparse FILE only."""
from pathlib import Path
import hashlib,json,subprocess,time

R=Path(__file__).resolve().parent
P=Path('/mnt/e/edk2-samurai-out/kernel248')
cfg=json.loads((P/'userdata-server-config-private.json').read_text())
state=json.loads((P/'userdata-worker-state-private.json').read_text())['state']
assert state['state']=='complete' and state['partclone_exit_code']==state['zstd_exit_code']==0
normalized=json.loads((P/'userdata-normalization-validation-private.json').read_text());assert normalized['phase']=='complete' and normalized['partclone_chkimg_exit_code']==0
source=Path(normalized['clean_path']);work=Path('/home/cy122/x2pro-linux/gnss248-return-validation');assert source.parent==work;attempt=cfg['state_dir'].rsplit('-',1)[1]
progress=P/f'userdata-host-validation-{attempt}-progress-private.json'
report=dict(stage=248,attempt=attempt,source_compressed_bytes=state['bytes_generated'],source_compressed_sha256=state['sha256'],source_full_sha_verified_before_normalization=True,removed_library_diagnostic_bytes=normalized['removed_library_diagnostic_bytes'])

def save(stage):
 report['phase']=stage;progress.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(dict(phase=stage,attempt=attempt)),flush=True)

def pipe_check(tool,args,label):
 with (P/f'userdata-{attempt}-{label}-private.log').open('xb') as log:
  z=subprocess.Popen(['zstd','-d','-c',str(source)],stdout=subprocess.PIPE,stderr=log)
  child=subprocess.Popen([tool,*args],stdin=z.stdout,stdout=log,stderr=log);z.stdout.close()
  child_rc=child.wait();z_rc=z.wait()
 assert child_rc==z_rc==0,(label,child_rc,z_rc)
 report[label+'_exit_code']=child_rc;report[label+'_zstd_exit_code']=z_rc

save('hashing_normalized_image')
assert source.stat().st_size==normalized['clean_bytes']
digest=hashlib.sha256()
with source.open('rb') as f:
 while b:=f.read(8*1024*1024):digest.update(b)
assert digest.hexdigest()==normalized['clean_sha256']
report.update(compressed_length_matches_source=True,compressed_sha256_matches_source=True,clean_compressed_bytes=source.stat().st_size,clean_compressed_sha256=digest.hexdigest(),chkimg_exit_code=0,source_zstd_exit_code=normalized['source_zstd_exit_code'])
save('restoring_to_pc_sparse_file')
dest=work/f'linux-userdata-restored-{attempt}-private.raw'
assert dest.parent==work and not dest.exists()
pipe_check('partclone.restore',['-W','-s','-','-o',str(dest),'-L',str(P/f'userdata-{attempt}-restore-internal-private.log')],'restore')
assert dest.stat().st_size==119033245696
report.update(restored_logical_bytes=dest.stat().st_size,restored_allocated_bytes=dest.stat().st_blocks*512,restored_to_regular_file_only=True)
save('checking_restored_f2fs_read_only')
with (P/f'userdata-{attempt}-restored-fsck-private.log').open('xb') as log:
 x=subprocess.run(['fsck.f2fs','--dry-run','--no-kernel-check','-f',str(dest)],stdout=log,stderr=log,timeout=1800)
assert x.returncode==0
report.update(restored_fsck_exit_code=0,phone_userdata_not_written=True,source_backed_up_offline_read_only=True)
save('complete')
(R/'userdata-backup-validation.json').write_text(json.dumps(report,indent=2)+'\n')
(P/'userdata-backup-validation.json').write_text(json.dumps(report,indent=2)+'\n')
