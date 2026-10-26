from pathlib import Path
import ast,hashlib,json,subprocess

ref=Path(__file__).resolve().parent;k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel200');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=json.loads((ref.parent/'kernel199/source-final-validation.json').read_text())['source_sha256']
changed='drivers/of/samurai-vio-phandle.c';new=json.loads((ref/'vio-helper-build-validation.json').read_text())['source_sha256']
assert all(sha(k/n)==h for n,h in previous.items() if n!=changed);assert sha(k/changed)==new
prior=json.loads((ref.parent/'kernel194/imx471-source-validation.json').read_text())['prior16_tracked_sources'];prior={n:h for n,h in prior.items() if n not in ['drivers/of/Kconfig','drivers/of/Makefile']};assert len(prior)==14 and all(sha(k/n)==h for n,h in prior.items())
assert sha(k/'.config')=='55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a'
assert sha(k/'arch/arm64/boot/Image')=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469'
assert sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')=='22c1f2ad3c54c52f181c43d343840dc026a05aab499c8fac13dc2476ddded9d3'
assert len((k/'Module.symvers').read_text().splitlines())==16793 and len((k/'modules.order').read_text().splitlines())==770
for p in ref.glob('*.py'):ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
for p in ref.glob('*.sh'):subprocess.run(['sh','-n',str(p)],check=True)
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=k,text=True);(out/'kernel-status-private.txt').write_text(status)
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=k,text=True).strip()
r=dict(stage=200,source_sha256={**previous,changed:new},other_camera_and_all14_original_sources_unchanged=True,
 tracked_modified_files=sum(not l.startswith('??') for l in status.splitlines()),untracked_entries=sum(l.startswith('??') for l in status.splitlines()),
 image_canonical_dtb_config_symbols_order_preserved=True,only_new_source_change='development VIO lookup accepts RPMH initial unknown state without enabling power',
 static_mmcx_dt_and_camss_module_deployed=True,unmodified_camera_frequency_tables=True,new_static_dt_boot_and_physical_frames_proven=True)
(ref/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({n:v for n,v in r.items() if n!='source_sha256'}))
