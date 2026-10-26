"""Confirm that the deployed GTK renderer actually submitted GMEM commands."""
from pathlib import Path
import hashlib,json,os,runpy,subprocess,tarfile
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel149')
out=Path('/mnt/e/edk2-samurai-out/kernel149')
archive=out/'deployed-settings-gmem-private.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='3d9c6aec6d1943b04af810906a8b79d992ff27e36dadc72ed766fd79f4f315e3'
with tarfile.open(archive) as t:
    entries=[m for m in t if m.isfile() and '/tu_' in m.name and m.name.endswith('.rd.gz')]
    assert len(entries)==1
    rd=out/'settings-command-private.rd.gz';rd.write_bytes(t.extractfile(entries[0]).read())
runpy.run_path(str(ref.parent/'kernel118/ensure-build-volume.py'))
mesa=Path('/home/cy122/pmos-samurai-kernel118/mesa-offline')
failed=out/'settings-command-private.txt'
if failed.exists():
    saved=out/'settings-command-first12-timeout-private.txt'
    assert not saved.exists()
    failed.rename(saved)
    (ref/'settings-decoder-first12-failure.json').write_text(json.dumps(dict(
        decoded_through_requested_frame=12,completed=False,error='TimeoutExpired',
        deadline_seconds=90,partial_output_bytes=saved.stat().st_size),indent=2)+'\n')
log=out/'settings-command-frame4-private.txt'
with log.open('wb') as f:
    subprocess.run([str(mesa/'decode-build/src/freedreno/decode/cffdump'),'--once','--frame=4',str(rd)],
        env=dict(os.environ,RNN_PATH=str(mesa/'mesa-26.2.4/src/freedreno/registers')),
        stdout=f,stderr=subprocess.STDOUT,check=True,timeout=90)
s=log.read_text(errors='replace')
report=dict(command_frame_four_decoded=True,bin_render_start=s.count('RM6_BIN_RENDER_START'),
    bin_resolve=s.count('RM6_BIN_RESOLVE'),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
    decoder_scope='Only frame four of the GTK Vulkan device command stream',
    first_twelve_frame_attempt_timed_out=True,
    first_three_completed_without_gmem=True,
    initial_first_three_gmem_assertion_failed=True)
assert report['bin_render_start']>0 and report['bin_resolve']>0
(ref/'settings-command-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
