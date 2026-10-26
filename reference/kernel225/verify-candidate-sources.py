from pathlib import Path
import hashlib,json,os,re,shutil,stat,subprocess

here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel225');sdk=Path('/home/cy122/x2pro-linux/libcamera214-root')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((here/'r13-package-build-validation.json').read_text())['original214_files_links_modes_restored']==2254
assert json.loads((here/'r13-agc-control-regression-validation.json').read_text())['behavioral_assertions']==48
original=json.loads((private/'original214-work-manifest-private.json').read_text());assert len(original)==2254
for n,item in original.items():
 p=sdk/'work/libcamera'/n
 if 'target' in item:assert p.is_symlink() and os.readlink(p)==item['target']
 else:assert not p.is_symlink() and sha(p)==item['sha256'] and stat.S_IMODE(p.stat().st_mode)==item['mode']
assert not list((sdk/'private').glob('libcamera214-before225*'))
recipe=sdk/'work/libcamera225-r13';assert len(list(recipe.glob('*.patch')))==20
lock=json.loads((repo/'linux-port/packages/libcamera/source-lock.json').read_text());assert lock['new_recipe_version']=='99990.7.2-r11'
assert all(sha(repo/'linux-port/packages/libcamera'/n)==v for n,v in lock['source_files_sha256'].items())
assert all(sha(recipe/n)==v for n,v in lock['source_files_sha256'].items() if n!='APKBUILD')
proofs=[('0018-simple-manual-exposure-controls.patch','candidate-source-validation.json'),('0019-ipc-threaded-start-outputs.patch','generator-source-validation.json'),('0020-soft-invalid-statistics-hold.patch','statistics-hold-source-validation.json')]
expected={};originals={};base=sdk/'work/libcamera224-r11-built/src/libcamera-v0.7.2'
for patch,proof_name in proofs:
 proof=json.loads((here/proof_name).read_text());assert sha(recipe/patch)==proof['patch_sha256']
 for n,v in proof['original_sources_sha256'].items():
  if n not in originals:originals[n]=v
 expected.update(proof['source_files'])
assert all(sha(base/n)==v for n,v in originals.items())
assert all(sha(sdk/'work/libcamera225-r13-built/src/libcamera-v0.7.2'/n)==v for n,v in expected.items())
replay=private/'candidate-patch-replay';assert not replay.exists();replay.mkdir(mode=0o700)
for n in originals:
 p=replay/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(base/n,p)
for patch,proof_name in proofs:
 proof=json.loads((here/proof_name).read_text());assert all(sha(replay/n)==v for n,v in proof['original_sources_sha256'].items())
 p=subprocess.run(['patch','--batch','--forward','-p1','-i',str(recipe/patch)],cwd=replay,capture_output=True)
 (private/(patch+'.replay-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
 assert all(sha(replay/n)==v for n,v in proof['source_files'].items())
assert all(sha(replay/n)==v for n,v in expected.items())
assert (sdk/'private/agc-control-preflight225.cpp').read_bytes()==(sdk/'private/agc-control-regression225-r13.cpp').read_bytes()==(here/'agc-control-regression.cpp').read_bytes()
b=sdk/'work/libcamera225-r13-built/src/libcamera-v0.7.2'
assert (b/'src/libcamera/camera.cpp').read_bytes()==(base/'src/libcamera/camera.cpp').read_bytes()
generated=re.sub(r'\s+','',(b/'output/include/libcamera/ipa/soft_ipa_proxy.h').read_text())
assert 'returnipa_->start(controls,sensorControls,source);' in generated
report=dict(stage=225,source_files_verified=len(expected),recipe_patch_count=20,prior17_inputs_preserved=True,
 three_patches_replay_exactly_in_order=True,original214_files_links_modes_preserved=2254,no_pending_original_snapshot=True,
 canonical_product_recipe_still_verified_r11=True,camera_core_ae_enable_preprocessing_unchanged=True,
 same_behavioral_test_source_failed_r12_and_passed_r13=True,generated_threaded_start_forwards_all_outputs=True,
 phone_deployment_not_claimed=True)
(here/'candidate-final-source-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
