from pathlib import Path
import hashlib,json,os,stat,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel220');root=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
files=list(here.glob('*.py'))
for p in files:compile(p.read_text(),str(p),'exec')
recipe=repo/'linux-port/packages/libcamera';lock=json.loads((recipe/'source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r7'
assert all(sha(recipe/name)==digest for name,digest in lock['source_files_sha256'].items())
assert (repo/'linux-port/packages/samurai-camera-config/configuration.yaml').read_bytes()==(repo/'linux-port/camera/configuration.yaml').read_bytes()
proof=json.loads((here/'candidate-source-validation.json').read_text())
assert all(sha(root/'work/libcamera220-built/src/libcamera-v0.7.2'/name)==digest for name,digest in proof['source_files'].items())
original=json.loads((private/'original214-work-manifest-private.json').read_text());actual={};work=root/'work/libcamera'
for p in work.rglob('*'):
 if p.is_symlink():actual[str(p.relative_to(work))]=dict(target=os.readlink(p))
 elif p.is_file():actual[str(p.relative_to(work))]=dict(sha256=sha(p),mode=stat.S_IMODE(p.stat().st_mode))
assert actual==original and len(actual)==2254
kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
assert sha(kernel/'drivers/media/i2c/imx471.c')=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175'
p=subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True);(private/'kernel-final-diff-check-private.log').write_bytes(p.stdout+p.stderr);assert p.returncode==0
r=dict(stage=220,python_sources_compile=len(files),current_recipe_and_source_locks_exact=True,configuration_payload_copies_exact=True,
 three_built_source_hashes_exact=True,original214_files_links_modes_restored=len(actual),host_kernel_source_still216=True,
 kernel_diff_check_exit=0,next_session_bytes=(repo/'NEXT-SESSION.md').stat().st_size)
assert r['next_session_bytes']<=6500
(here/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
