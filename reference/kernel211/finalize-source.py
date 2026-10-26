from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;repo=here.parents[1];kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');private=Path('/mnt/e/edk2-samurai-out/kernel211')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((private.parent/'kernel210/source-before/source-file-hashes-private.json').read_text())
intentional={'drivers/media/i2c/imx471.c':'c9c4a751521502599ffe0de46bfacc00b9c29237320ee3a7a13d977cc70e8417','arch/arm64/boot/dts/qcom/sm8150-samurai.dts':'c25ab5b7dc4723798e590110cb84a5d02cb36313ba0feda98981e75ac1f2913a','Documentation/devicetree/bindings/media/i2c/sony,imx471.yaml':'f21155bbb16a062f612bbf58773452b5b59421e3bc4676775b2d58b71da44e74'}
assert {name for name,digest in old.items() if sha(kernel/name)!=digest}==set(intentional)
assert all(sha(kernel/name)==digest for name,digest in intentional.items())
before=json.loads((private/'source-before/hashes-private.json').read_text())
preserved=['.config','Module.symvers','modules.order','arch/arm64/boot/Image','arch/arm64/boot/dts/qcom/sm8150-samurai.dtb']
assert all(sha(kernel/name)==before[name] for name in preserved)
assert len((kernel/'Module.symvers').read_text().splitlines())==16798 and len((kernel/'modules.order').read_text().splitlines())==772
for p in here.glob('*.py'):ast.parse(p.read_text(),filename=str(p))
status=subprocess.check_output(['git','status','--porcelain','--untracked-files=normal'],cwd=kernel,text=True);(private/'kernel-status-final-private.txt').write_text(status)
check=subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True);(private/'kernel-diff-check-private.log').write_bytes(check.stdout+check.stderr);assert check.returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=kernel).strip()
lock=json.loads((repo/'linux-port/radio/source-lock.json').read_text());assert all(sha(repo/'linux-port/radio'/name)==digest for name,digest in lock['own_sources'].items())
report=dict(stage=211,three_intentional_source_changes=intentional,other_33_saved_source_files_preserved=True,config_symbols_order_image_and_old_canonical_dtb_preserved=True,combined_symbols=16798,modules_order=772,tracked_modified_files=sum(not line.startswith('??') for line in status.splitlines()),untracked_entries=sum(line.startswith('??') for line in status.splitlines()),kernel_diff_check_passed=True,no_source_staged=True,reference_python_syntax_passed=True,radio_source_lock_preserved=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
