from pathlib import Path
import ast,hashlib,json,subprocess

ref=Path(__file__).resolve().parent;repo=ref.parents[1];k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel203')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=json.loads((ref.parent/'kernel200/source-final-validation.json').read_text())['source_sha256'];assert all(sha(k/n)==h for n,h in previous.items())
assert sha(k/'.config')=='55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a'
assert sha(k/'arch/arm64/boot/Image')=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469'
assert sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')=='22c1f2ad3c54c52f181c43d343840dc026a05aab499c8fac13dc2476ddded9d3'
assert len((k/'Module.symvers').read_text().splitlines())==16793 and len((k/'modules.order').read_text().splitlines())==770
for p in [*ref.rglob('*.py'),*(repo/'linux-port/packages').rglob('*.py')]:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
assist=repo/'linux-port/packages/samurai-gnss-assist'
for name in ['samurai-gnss-assist.initd','post-install','pre-deinstall']:subprocess.run(['sh','-n',str(assist/name)],check=True)
assert sha(assist/'samurai-gnss-assist.py')=='42168f33472d01dbf115ea766487c70d95332aabc8de02c25bdb381cea80af97'
assert sha(assist/'samurai-gnss-assist.initd')=='54b8174507e97badfafba6c373ebf937045c1c85034f094e7de910369af78af3'
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=k,text=True);(out/'kernel-status-private.txt').write_text(status)
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=k,text=True).strip()
r=dict(stage=203,all_kernel200_sources_unchanged=True,source_sha256=previous,image_config_canonical_dtb_symbols_order_unchanged=True,
 tracked_modified_files=sum(not l.startswith('??') for l in status.splitlines()),untracked_entries=sum(l.startswith('??') for l in status.splitlines()),
 assist_source_sha256=sha(assist/'samurai-gnss-assist.py'),assist_initd_sha256=sha(assist/'samurai-gnss-assist.initd'),
 canonical_package_and_stage_python_syntax_pass=True,init_and_package_hook_shell_syntax_pass=True,kernel_rebuild_not_needed=True)
(ref/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({n:v for n,v in r.items() if n!='source_sha256'}))
