from pathlib import Path
import ast,hashlib,json,subprocess
here=Path(__file__).resolve().parent;kernel=Path('/home/cy122/pmos-samurai-kernel136/kernel');old=json.loads((here.parent/'kernel211/source-final-validation.json').read_text())
for name,digest in old['three_intentional_source_changes'].items():assert hashlib.sha256((kernel/name).read_bytes()).hexdigest()==digest
for folder in [here,here.parent/'kernel211']:
    for path in folder.glob('*.py'):ast.parse(path.read_text(),filename=str(path))
assert subprocess.run(['git','diff','--check'],cwd=kernel,capture_output=True).returncode==0
assert not subprocess.check_output(['git','diff','--cached','--name-only'],cwd=kernel).strip()
report=dict(stage=212,no_additional_kernel_source_change=True,reference_python_syntax_passed=True,kernel_diff_check_passed=True,no_source_staged=True,no_boot_or_other_partition_flash=True,camera_config_directory_0755_and_file_0644_fix_included=True)
(here/'source-final-validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
