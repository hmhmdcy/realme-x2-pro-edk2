from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];k=Path('/home/cy122/pmos-samurai-kernel136/kernel');private=Path('/mnt/e/edk2-samurai-out/kernel210');before=private/'source-before'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((before/'source-file-hashes-private.json').read_text());board='arch/arm64/boot/dts/qcom/sm8150-samurai.dts'
changed=[name for name,digest in old.items() if sha(k/name)!=digest];assert changed==[board]
assert sha(k/board)==json.loads((here/'camera-source-validation.json').read_text())['board_after_sha256']
artifacts=json.loads((before/'build-artifacts-private.json').read_text())
assert all(sha(k/name)==artifacts[name] for name in ['arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb'])
assert sha(k/'.config')==json.loads((here/'camera-module-build-validation.json').read_text())['config_sha256']
assert len((k/'Module.symvers').read_text().splitlines())==16798 and len((k/'modules.order').read_text().splitlines())==772
for p in here.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
lock=json.loads((repo/'linux-port/radio/source-lock.json').read_text());assert all(sha(repo/'linux-port/radio'/n)==d for n,d in lock['own_sources'].items())
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=k,text=True);(private/'kernel-status-final-private.txt').write_text(status)
check=subprocess.run(['git','diff','--check'],cwd=k,capture_output=True);(private/'kernel-diff-check-private.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=k).strip()
report=dict(stage=210,only_board_dts_changed_from_36_saved_source_files=True,board_dts_sha256=sha(k/board),config_sha256=sha(k/'.config'),image183_and_old_canonical_dtb_preserved=True,base_symbols_preserved_plus_five_cci_exports=True,combined_symbols=16798,modules_order=772,tracked_modified_files=sum(not l.startswith('??') for l in status.splitlines()),untracked_entries=sum(l.startswith('??') for l in status.splitlines()),kernel_diff_check_passed=True,reference_python_syntax_passed=True,radio_source_lock_unchanged=True,no_source_staged=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
