"""Read exact-kernel module pin rules and the built target's source dependency delta."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import re
import subprocess

HERE = Path(__file__).resolve().parent
PRIVATE = Path('/mnt/e/edk2-samurai-out/kernel455')
spec = importlib.util.spec_from_file_location('review455_storage449', HERE.parent / 'kernel449/storage.py')
storage = importlib.util.module_from_spec(spec); spec.loader.exec_module(storage)
shared = storage.mount.mounted_build()
original = shared.parent / 'source354'
source = shared.parent / 'kernel455-lens-private/source-view'
build = shared.parent / 'kernel455-lens-private/O'
record = json.loads((HERE.parent / 'kernel363/boot-candidate-build-validation.json').read_text())
git = lambda *args: subprocess.check_output(['git', '-C', str(original), *args],env=dict(os.environ,GIT_OPTIONAL_LOCKS='0'))
assert not git('status','--porcelain')
cmd = (build / 'drivers/media/i2c/.bu64253.o.cmd').read_text()
paths = set(re.findall(re.escape(str(source)) + r'/([^\s\\]+)',cmd))
dependencies = sorted(p for p in paths if (source / p).is_file())
tracked = set(git('ls-files', '--', *dependencies).decode().splitlines())
untracked = sorted(set(dependencies) - tracked - {'drivers/media/i2c/bu64253.c'})
assert not untracked, untracked
changed = set(git('diff','--name-only',record['commit'],'HEAD').decode().splitlines())
intersection = sorted(changed & set(dependencies))
assert not intersection, intersection
assert 'drivers/media/i2c/bu64253.c' in dependencies
module_source = original / 'kernel/module/main.c'
module_raw = module_source.read_bytes()
(PRIVATE / 'kernel-module-main-private.c').write_bytes(module_raw)
raw = module_raw.decode()
interesting = ['try_stop_module', 'try_module_get', 'module_put', 'MODULE_STATE_GOING', 'MODULE_FORCE_UNLOAD']
lines = {token:[i for i,line in enumerate(raw.splitlines(),1) if token in line] for token in interesting}
config = (PRIVATE.parent / 'kernel453/image363-config-private').read_text()
module_config = [l for l in config.splitlines() if l.startswith(('CONFIG_MODULES=', 'CONFIG_MODULE_UNLOAD=', 'CONFIG_MODULE_FORCE_UNLOAD=', '# CONFIG_MODULE_FORCE_UNLOAD '))]
report = dict(stage=455, scope='static source evidence for module reference rules and actual compiler source dependencies',
              kernel363_commit=record['commit'], current_source_head=git('rev-parse','HEAD').decode().strip(),
              actual_source_file_dependencies=len(dependencies), original_driver_source_replaced=True,
              other_source_dependencies_tracked=len(tracked), unexpected_untracked_source_dependencies=untracked,
              post_k363_changed_paths_in_compiler_dependencies=intersection,
              all_other_tracked_source_dependencies_unchanged_since_k363=True,
              dependency_command_sha256=hashlib.sha256(cmd.encode()).hexdigest(),
              module_main_sha256=hashlib.sha256(module_raw).hexdigest(), module_source_key_lines=lines,
              image363_module_configuration=module_config,
              normal_nonforced_module_unload_only=True, no_runtime_module_unload_test=True,
              shared_or_453_inputs_modified=False, sdk_or_phone_accessed=False)
(PRIVATE / 'compiler-dependencies-private.json').write_text(json.dumps(dependencies,indent=2)+'\n')
(HERE / 'framework-review-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
