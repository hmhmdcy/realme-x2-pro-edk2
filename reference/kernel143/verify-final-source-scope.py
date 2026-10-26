from pathlib import Path
import ast
import hashlib
import json
import re
import subprocess

root=Path('/home/cy122/pmos-samurai-kernel136/kernel')
ref=Path('/mnt/e/RealmeX2Pro edk2/reference/kernel143')
out=Path('/mnt/e/edk2-samurai-out/kernel143')
old=out.joinpath('source-diff-before-private.patch').read_bytes()
new=subprocess.check_output(['git','-C',str(root),'diff','--binary'])
def split(text):
    return {block.split(b'\n',1)[0]:block for block in re.split(rb'(?m)(?=^diff --git )',text) if block}
a=split(old);b=split(new)
key=b'diff --git a/drivers/tty/serial/eud.c b/drivers/tty/serial/eud.c'
assert a.keys()==b.keys()
assert [name for name in a if a[name]!=b[name]]==[key]
assert root.joinpath('drivers/tty/serial/eud.c').read_bytes()==out.joinpath('eud-candidate-private.c').read_bytes()
bundle=json.loads(ref.joinpath('threaded-console-build-package-validation.json').read_text())
assert hashlib.sha256(root.joinpath('arch/arm64/boot/Image').read_bytes()).hexdigest()==bundle['image_sha256']
assert hashlib.sha256(out.joinpath('Image-k143-threaded-console-private').read_bytes()).hexdigest()==bundle['image_sha256']
for file in ref.glob('*.py'):ast.parse(file.read_text())
for file in ref.glob('*.sh'):subprocess.run(['bash','-n',str(file)],check=True)
assert 'python3 /tmp/k143-check-known-quiesce-warning.py' in ref.joinpath('freeze-for-bootloader.sh').read_text()
assert 'target_kernel=143' in ref.joinpath('verify-quiesce.py').read_text()
report=dict(stage=143,only_changed_source_from140='drivers/tty/serial/eud.c',
    full_git_diff_outside_eud_byte_identical=True,archived_candidate_matches_source=True,
    built_image_matches_package=True,python_shell_syntax_pass=True,
    exact_old140_shutdown_warning_guarded=True,slimbus_lifecycle_not_changed=True,goal_complete=False)
ref.joinpath('final-source-scope-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print('K143_FULL_SOURCE_SCOPE_AND_CURRENT_IMAGE_PACKAGE_GUARDS_PASS')
