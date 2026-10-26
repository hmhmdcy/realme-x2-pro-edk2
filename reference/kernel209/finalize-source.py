from pathlib import Path
import ast,hashlib,json,subprocess

here=Path(__file__).resolve().parent
repo=here.parents[1]
k=Path('/home/cy122/pmos-samurai-kernel136/kernel')
out=Path('/mnt/e/edk2-samurai-out/kernel209')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=json.loads((here.parent/'kernel204/source-final-validation.json').read_text())
assert all(sha(k/name)==digest for name,digest in previous['previous_source_sha256'].items())
assert sha(k/'arch/arm64/boot/dts/qcom/sm8150-samurai.dts')==previous['board_dts_sha256']
expected={'.config':'55f1f0a35bd4f20ad70ebd383a8863e05d0b6d53a07c0f0f09fb47cee057913a','arch/arm64/boot/Image':'bfa72dd920c8376ceefc458fe7202a73ddb364b6727556471d70c8d0e7ade469','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb':'22c1f2ad3c54c52f181c43d343840dc026a05aab499c8fac13dc2476ddded9d3'}
assert all(sha(k/name)==digest for name,digest in expected.items())
assert len((k/'Module.symvers').read_text().splitlines())==16793
assert len((k/'modules.order').read_text().splitlines())==770
for p in [*here.rglob('*.py'),* (repo/'linux-port/radio').glob('*.py')]:
    ast.parse(p.read_text(encoding='utf-8-sig'),filename=str(p))
subprocess.run(['sh','-n',str(repo/'linux-port/radio/samurai-wifi.sh')],check=True)
lock=json.loads((repo/'linux-port/radio/source-lock.json').read_text())
assert all(sha(repo/'linux-port/radio'/name)==digest for name,digest in lock['own_sources'].items())
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=k,text=True)
(out/'kernel-status-private.txt').write_text(status)
check=subprocess.run(['git','diff','--check'],cwd=k,capture_output=True)
(out/'kernel-diff-check-private.log').write_bytes(check.stdout+check.stderr)
assert check.returncode==0 and not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=k).strip()
result=dict(stage=209,kernel_sources_match204_after_diagnostic_revert=True,image_config_canonical_dtb_symbols_order_unchanged=True,
    tracked_modified_files=sum(not line.startswith('??') for line in status.splitlines()),untracked_entries=sum(line.startswith('??') for line in status.splitlines()),
    kernel_diff_check_passed=True,no_kernel_rebuild_or_flash=True,python_and_startup_shell_syntax_passed=True,radio_source_lock_all_own_hashes_match=True)
(here/'source-final-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
