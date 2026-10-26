from pathlib import Path
import difflib,hashlib,json,os,shutil,subprocess
k=Path('/home/cy122/pmos-samurai-kernel136/kernel');base=k/'drivers/media/platform/qcom/camss';ref=Path(__file__).resolve().parent;out=Path('/mnt/e/edk2-samurai-out/kernel198');names=['camss.c','camss-vfe.c','camss.h'];original={n:(base/n).read_bytes() for n in names};state={n:(k/n).read_bytes() for n in ['.config','Module.symvers','modules.order']};sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();image={n:sha(k/n) for n in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']};assert sha(base/'camss.c')=='cc212a4c8674e15fe93a8fba3801fb6850596b7960e1a1df9ab4984ef1633ca2';env=dict(os.environ,KBUILD_BUILD_VERSION='183',PATH='/home/cy122/.cargo/bin:'+os.environ['PATH'],RUSTUP_HOME='/home/cy122/.rustup');modified={};patch=''
try:
 subprocess.run(['git','apply',str(ref/'temporary-clock-diagnostic.patch')],cwd=k,check=True,capture_output=True)
 p=base/'camss.c';s=p.read_text();start=s.index('static const struct camss_subdev_resources csid_res_8150[]');end=s.index('static const struct camss_subdev_resources csiphy_res_8250[]',start);block=s[start:end]
 pairs=[('{ 19200000, 400000000, 558000000, 637000000, 847000000, 950000000 }','{ 19200000, 400000000 }',4),('{ 847000000 }','{ 400000000 }',4),('{ 19200000, 75000000, 400000000, 480000000, 600000000 }','{ 19200000, 75000000, 400000000 }',4),('{ 600000000 }','{ 400000000 }',4)]
 for old,new,count in pairs:assert block.count(old)==count,(old,block.count(old));block=block.replace(old,new)
 p.write_text(s[:start]+block+s[end:])
 for n in names:
  modified[n]=(base/n).read_bytes();path='drivers/media/platform/qcom/camss/'+n;patch+='diff --git a/'+path+' b/'+path+'\n'+''.join(difflib.unified_diff(original[n].decode().splitlines(True),modified[n].decode().splitlines(True),fromfile='a/'+path,tofile='b/'+path))
 (ref/'temporary-stock-low-clock-diagnostic.patch').write_text(patch)
 with (out/'stock-low-olddefconfig-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','olddefconfig'],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 targets=['drivers/media/common/videobuf2/videobuf2-'+n+'.ko' for n in ['common','memops','v4l2','dma-sg']]+['drivers/media/platform/qcom/camss/qcom-camss.ko']
 with (out/'stock-low-build-private.log').open('xb') as log:subprocess.run(['make','ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','LD=aarch64-linux-gnu-ld --no-keep-memory','W=1','-j3',*targets],cwd=k,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
 dest=out/'qcom-camss-stock-low.ko';assert not dest.exists();shutil.copyfile(k/targets[-1],dest);subprocess.run(['aarch64-linux-gnu-strip','--strip-debug',str(dest)],check=True)
finally:
 for n,b in original.items():(base/n).write_bytes(b)
 for n,b in state.items():(k/n).write_bytes(b)
assert all(sha(k/n)==h for n,h in image.items());diag=[s for s in (out/'stock-low-build-private.log').read_text().splitlines() if 'warning:' in s or 'error:' in s];assert not diag,diag
r=dict(stage=198,module_sha256=sha(dest),module_bytes=dest.stat().st_size,vermagic=subprocess.check_output(['modinfo','-F','vermagic',str(dest)],text=True).strip(),source_sha256={n:hashlib.sha256(b).hexdigest() for n,b in modified.items()},original_source_restored=True,image_dtb_config_symbols_order_restored=True,w1_diagnostics=0,vfe_and_csid_max_hz=400000000,other_soc_resources_unchanged=True,development_experiment_only=True,no_voltage_or_power_level_changes=True);(ref/'stock-low-module-build-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
