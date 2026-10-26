"""Publish the tested patch chain, independently replaying it on saved sources."""
from pathlib import Path
import hashlib,json,shutil,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];private=Path('/mnt/e/edk2-samurai-out/kernel219');kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((here/'full-mode-r4-finish-validation.json').read_text())['experimental_full_raw_disabled']
for w,h,v in [(1928,1088,-1),(2304,1728,-1),(2304,1728,396),(4608,3456,-1)]:
 r=json.loads((here/f'{w}x{h}-timing-vblank{v}-after-timing-fix-validation.json').read_text());assert r['frame_count']==120 and abs(r['fps_from_current_controls']/r['fps_from_hardware_timestamps']-1)<0.001
work=private/'patch-replay';assert not work.exists();work.mkdir(mode=0o700)
files=['drivers/media/i2c/imx471.c','arch/arm64/boot/dts/qcom/sm8150-samurai.dts'];before={}
for name in files:
 before[name]=sha(kernel/name);p=work/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(kernel/name,p)
assert before[files[0]]=='cc7562794d1a9b69a0bf7e98f7ed8fcb9e9917b7a6a5c46b833f649a8c60b175'
target=repo/'linux-port/camera/kernel';lock=json.loads((target/'source-lock.json').read_text());assert lock['stage']==216
added=[]
for source,name in [('imx471-factory-modes.patch','0003-imx471-factory-modes.patch'),('imx471-pixel-array-timing.patch','0004-imx471-pixel-array-timing.patch')]:
 patch=here/source;p=subprocess.run(['patch','--batch','--forward','-p1','-i',str(patch)],cwd=work,capture_output=True,timeout=10)
 (private/(name+'-replay-private.log')).write_bytes(p.stdout+p.stderr);assert p.returncode==0
 shutil.copyfile(patch,target/name);added.append(dict(file=name,sha256=sha(target/name),origin='verified real-device stage219, factory mode data stage217'))
expected={'drivers/media/i2c/imx471.c':private/'timing-source/imx471.c','arch/arm64/boot/dts/qcom/sm8150-samurai.dts':private/'timing-source/sm8150-samurai.dts'}
assert all((work/name).read_bytes()==p.read_bytes() for name,p in expected.items())
assert all(sha(kernel/name)==digest for name,digest in before.items())
lock['patches']+=added
lock.update(stage=219,current_source_sha256=sha(expected[files[0]]),current_board_source_sha256=sha(expected[files[1]]),
 current_module_sha256='e49dab26b05a325df8da64bb5c4b57c29cd51d1dcf15f5d4ed4dcb53033e66f1',module_bytes=29536,
 kernel_image_and_boot_unchanged=False,kernel_image_unchanged=True,boot_stage=219,
 deployed_dtb_sha256='a214fd6b2ccb93e5bbb5adc774e7c510398541e8fab286832682cc6bbd76ca42',
 additional_patch_base_source_hashes=before,patch_replay_exact=True,host_canonical_kernel_source_still_stage216=True,
 runtime_evidence='../../../reference/kernel219/timing-module-reload-validation.json',
 timing_evidence='../../../reference/kernel219/4608x3456-timing-vblank-1-after-timing-fix-validation.json',
 experimental_full_resolution_default=False,geometry_colour_quality_and_standard_cfa_still_open=True)
(target/'source-lock.json').write_text(json.dumps(lock,indent=2)+'\n')
r=dict(stage=219,public_driver_and_board_patch_chain_replayed_exact=True,additional_patches=added,
 source_and_board_match_deployed_candidate=True,host_canonical_source_not_overwritten=True,
 existing_kernel_changes_and_all_private_factory_inputs_preserved=True)
(here/'kernel-patch-integration-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
