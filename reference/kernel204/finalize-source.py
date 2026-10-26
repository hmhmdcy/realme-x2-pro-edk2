from pathlib import Path
import ast,hashlib,json,subprocess

here=Path(__file__).resolve().parent;repo=here.parents[1];k=Path('/home/cy122/pmos-samurai-kernel136/kernel');out=Path('/mnt/e/edk2-samurai-out/kernel204');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
prior=json.loads((here.parent/'kernel203/source-final-validation.json').read_text())['source_sha256'];assert all(sha(k/n)==h for n,h in prior.items())
uart=json.loads((here/'uart-candidate-validation.json').read_text());board=k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts';assert sha(board)==uart['source_candidate_sha256']
assert sha(k/'.config')=='55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a' and sha(k/'arch/arm64/boot/Image')=='bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469'
assert sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dtb')=='22c1f2ad3c54c52f181c43d343840dc026a05aab499c8fac13dc2476ddded9d3'
assert len((k/'Module.symvers').read_text().splitlines())==16793 and len((k/'modules.order').read_text().splitlines())==770
for p in [*here.rglob('*.py'),repo/'linux-port/ssc/samurai-ssc.py']:ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
for p in here.rglob('*.sh'):subprocess.run(['sh','-n',str(p)],check=True)
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=k,text=True);(out/'kernel-status-private.txt').write_text(status);subprocess.run(['git','diff','--check'],cwd=k,check=True,capture_output=True)
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=k,text=True).strip()
r=dict(stage=204,all_previous_kernel203_source_subset_unchanged=True,previous_source_sha256=prior,board_dts_sha256=sha(board),deployed_stable_phandle_dtb_sha256=uart['candidate_dtb_sha256'],
 kernel_image_config_modules_symbols_order_unchanged=True,old_canonical_dtb_not_overwritten=True,board_source_compiled_to_private_candidate=True,ssc_diagnostic_source_sha256=sha(repo/'linux-port/ssc/samurai-ssc.py'),
 tracked_modified_files=sum(not l.startswith('??') for l in status.splitlines()),untracked_entries=sum(l.startswith('??') for l in status.splitlines()),python_and_shell_syntax_pass=True,kernel_diff_check_pass=True,kernel_code_rebuild_not_needed=True)
(here/'source-final-validation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({n:v for n,v in r.items() if n!='previous_source_sha256'}))
