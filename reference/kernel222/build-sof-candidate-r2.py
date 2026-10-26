from pathlib import Path
import hashlib,json,os,shutil,stat,subprocess,time
here=Path(__file__).resolve().parent;private=Path('/mnt/e/edk2-samurai-out/kernel222');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');media=kernel/'drivers/media/platform/qcom/camss'
proof=json.loads((here/'sof-candidate-source-validation.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert all(sha(kernel/n)==h for n,h in proof['original_sources_sha256'].items())
assert sha(media/'camss.c')=='53d8a7102f28c5f33355b73ba65eb0ca6550529e777f316378ecee4517569412'
assert sha(media/'camss-cpas.c')=='3ee20b599365cb3d82aa904fc4e8dc48c9f5e3d8563d56ef43d6794dc52b06c5'
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  if (p/'comm').read_text().strip() in ['make','cc1','cc1plus','as','ld']:
   assert not (p/'cwd').resolve().is_relative_to(kernel),'Other kernel build live'
 except (FileNotFoundError,ProcessLookupError):pass
files={p for p in media.iterdir() if p.is_file() and not p.is_symlink()}
files|={p for p in (kernel/'drivers/media/common/videobuf2').iterdir() if p.is_file() and not p.is_symlink()}
files|={kernel/n for n in ['.config','Module.symvers','modules.order','include/generated/compile.h','include/generated/utsrelease.h','include/generated/autoconf.h','include/config/auto.conf','include/config/auto.conf.cmd']}
saved={str(p.relative_to(kernel)):dict(data=p.read_bytes(),mode=stat.S_IMODE(p.stat().st_mode)) for p in files}
snapshot=private/'kernel-before-sof-r2';assert not snapshot.exists();snapshot.mkdir(mode=0o700)
(private/(snapshot.name+'-mode-manifest-before-build-private.json')).write_text(json.dumps({name:dict(sha256=hashlib.sha256(item['data']).hexdigest(),mode=item['mode']) for name,item in saved.items()},indent=2)+'\n')
for name,item in saved.items():p=snapshot/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(item['data']);p.chmod(item['mode'])
preserved={name:sha(kernel/name) for name in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']}
state=dict(stage=222,phase='source-snapshot-verified',snapshot_files=len(saved),started=time.time());marker=private/'sof-build-r2-state-private.json'
def record(**values):state.update(values);marker.write_text(json.dumps(state,indent=2)+'\n')
record();env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup')
process=None;rc=None;dest=private/'qcom-camss-sof222.ko'
try:
 for name,digest in proof['candidate_sources_sha256'].items():
  data=(private/'sof-candidate-source'/name).read_bytes();assert hashlib.sha256(data).hexdigest()==digest;(kernel/name).write_bytes(data)
 command=['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3',*['drivers/media/common/videobuf2/videobuf2-'+n+'.ko' for n in ['common','memops','v4l2','dma-sg']],'drivers/media/platform/qcom/camss/qcom-camss.ko']
 with (private/'sof-kernel-build-r2-private.log').open('xb') as log:
  process=subprocess.Popen(command,cwd=kernel,env=env,stdout=log,stderr=subprocess.STDOUT);record(phase='kernel-module-build-live',pid=process.pid)
  try:rc=process.wait(timeout=3600)
  except subprocess.TimeoutExpired:record(phase='same-build-live-observation-expired');raise
 record(phase='terminal-restoration-pending',exit=rc)
 if rc==0:shutil.copyfile(media/'qcom-camss.ko',dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
finally:
 if process is None or process.poll() is not None:
  for p in list(media.iterdir())+list((kernel/'drivers/media/common/videobuf2').iterdir()):
   if p.is_file() and not p.is_symlink() and str(p.relative_to(kernel)) not in saved:p.unlink()
  for name,item in saved.items():p=kernel/name;p.write_bytes(item['data']);p.chmod(item['mode'])
  assert all((kernel/n).read_bytes()==item['data'] and stat.S_IMODE((kernel/n).stat().st_mode)==item['mode'] for n,item in saved.items())
  assert all(sha(kernel/n)==h for n,h in preserved.items());record(canonical_sources_objects_metadata_restored=True)
assert rc==0,'Inspect terminal build; original state restored'
vm=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip();assert vm=='7.3.0-rc6-rmx1931-samurai-k132+ SMP preempt mod_unload aarch64'
assert subprocess.check_output(['modinfo','-F','intree',str(dest)],text=True).strip()=='Y'
symbols={l.split()[1] for l in (kernel/'Module.symvers').read_text().splitlines()};nm=subprocess.check_output(['aarch64-linux-gnu-nm','-u',str(dest)],text=True);missing=[l.split()[-1] for l in nm.splitlines() if l.split()[-1] not in symbols];assert not missing,missing
diags=[l for l in (private/'sof-kernel-build-r2-private.log').read_text().splitlines() if 'warning:' in l or 'error:' in l];assert not diags,diags
style=subprocess.run(['perl',str(kernel/'scripts/checkpatch.pl'),'--no-tree','--no-signoff',str(here/'camss-sm8150-sof-candidate.patch')],capture_output=True,text=True);(private/'sof-checkpatch-private.log').write_text(style.stdout+style.stderr)
r=dict(stage=222,candidate_only=True,compiled_module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=vm,intree=True,w1_diagnostics=0,import_symbols_available=True,checkpatch_exit=style.returncode,canonical_sources_objects_and_metadata_restored=True,source_files_preserved=len(saved),images_and_canonical_dtb_unchanged=True,phone_not_yet_modified=True,dependency_vb2_modules_built_for_modpost=True,initial_missing_dependency_modpost_failure_preserved=True)
(here/'sof-candidate-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');record(phase='candidate-built-canonical-restored',terminal=True);print(json.dumps(r))
