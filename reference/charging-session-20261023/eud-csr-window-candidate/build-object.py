"""Compile only the private EUD object with the existing Image's saved command.

No make/config regeneration, SDK, binding changes, or shared output writes.
"""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess

HERE = Path(__file__).resolve().parent
helper = HERE.parents[1] / 'kernel284/storage.py'
spec = importlib.util.spec_from_file_location('original_storage', helper)
storage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(storage)
build = storage.mounted_build()
source = (build / 'source').resolve()
saved_path = build / 'drivers/tty/serial/.eud.o.cmd'
saved_raw = saved_path.read_bytes()
line = saved_raw.decode().splitlines()[0]
assert line.startswith('savedcmd_drivers/tty/serial/eud.o := ')
argv = shlex.split(line.split(' := ', 1)[1])
assert argv[0] == 'aarch64-linux-gnu-gcc' and argv.count('-o') == 1
assert '-DKBUILD_EXTRA_WARN1' in argv
assert argv[-1] == str(source / 'drivers/tty/serial/eud.c')
sha = lambda b: hashlib.sha256(b).hexdigest()
assert sha((source / 'drivers/tty/serial/eud.c').read_bytes()) == '16670a85501bf1bb1d8ae5bd856d991a73ac199028e33275f34f1774991c7bfd'
out = HERE / 'object-build'
out.mkdir(exist_ok=True)
(out / 'tmp').mkdir(exist_ok=True)
argv[argv.index('-o') + 1] = str(out / 'eud.o')
argv[-1] = str(HERE / 'eud.c')
dependency = '-Wp,-MMD,drivers/tty/serial/.eud.o.d'
assert argv.count(dependency) == 1
argv[argv.index(dependency)] = '-Wp,-MMD,' + str(out / 'eud.d')
argv.insert(1, '-Werror')
before = {p: sha((build / p).read_bytes()) for p in ['.config', 'include/generated/autoconf.h',
          'include/generated/utsrelease.h', 'drivers/tty/serial/eud.o', 'drivers/tty/serial/.eud.o.cmd']}
run = subprocess.run(argv, cwd=build, env={**os.environ, 'TMPDIR': str(out / 'tmp')}, capture_output=True)
after = {p: sha((build / p).read_bytes()) for p in before}
result = {'passed': run.returncode == 0 and before == after,
          'compile_returncode': run.returncode, 'stdout': run.stdout.decode(), 'stderr': run.stderr.decode(),
          'candidate_sha256': sha((HERE / 'eud.c').read_bytes()),
          'header_sha256': sha((HERE / 'eud-com-window.h').read_bytes()),
          'saved_command_sha256': sha(saved_raw), 'build': str(build), 'source': str(source),
          'object_sha256': sha((out / 'eud.o').read_bytes()) if not run.returncode else None,
          'shared_inputs_unchanged': before == after, 'make_invoked': False, 'sdk_invoked': False,
          'phone_accessed': False, 'ssh_executed': False, 'kernel_or_module_linked': False,
          'scope': 'single private arm64 EUD object; existing W=1 saved command plus Werror'}
(HERE / 'object-build-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result, indent=2))
raise SystemExit(0 if result['passed'] else 1)
