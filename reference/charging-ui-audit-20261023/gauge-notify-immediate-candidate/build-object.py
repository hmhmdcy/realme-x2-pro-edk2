"""Compile only the changed BQ object from its saved private W=1 command."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import os
import shlex
import subprocess
import sys
import time

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
OLD = Path('/home/cy122/charging-management-20261023/gauge-current-samurai-candidate')
BUILD = OLD / 'kbuild'
SOURCE = OLD / 'source-view'
OUT = Path('/home/cy122/charging-management-20261023/gauge-notify-immediate-object-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    expected = {
        'bq27xxx_battery.c': '0014077792948460fc2a2e9581225dc684cba4d5bff95c3e88767d661ce5439b',
        'notify-immediate.patch': 'a912e335bb098b52ef90042e17eab845be295f2ba2bfd3348a204fbb1dd425e8',
        'test-result.json': '4acaad595b9d18c160b93763f1b2da42244393c659cc504dd2e3c1b89a355f90',
    }
    assert all(sha(HERE / n) == h for n, h in expected.items())
    tested = json.loads((HERE / 'test-result.json').read_bytes())
    assert tested['passed'] and tested['group_count'] == 7
    assert tested['files']['bq27xxx_battery.c'] == expected['bq27xxx_battery.c']
    if not args.execute:
        print(json.dumps({'passed': True, 'mode': 'check-local', 'compiler_invoked': False,
                          'storage_helper_invoked': False, 'files': expected}))
        return

    assert os.geteuid() == 0, 'Use the original Ubuntu/root guard; no UID fallback'
    assert not OUT.exists(), 'Unique output already exists; do not replay'
    assert not (HERE / 'object-build-result.json').exists(), 'Original receipt must remain untouched'
    OUT.mkdir(parents=True)
    (OUT / 'tmp').mkdir()
    result = {'passed': False, 'private_output': str(OUT), 'compiler_invoked': False,
              'make': False, 'SDK': False, 'Git': False, 'phone_access': False,
              'Image_module_or_other_object_linked': False}
    try:
        helper = REF / 'kernel284/storage.py'
        assert sha(helper) == '5cddb34d1c6db70a8a2d1df18bf753a9f6759714fa8c0bfa8b5a2952c5a7d42c'
        spec = importlib.util.spec_from_file_location('gauge_notify_storage284', helper)
        storage = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(storage)
        shared = storage.mounted_build()
        assert shared == Path('/mnt/samurai-full282/build')
        result['storage_helper_sha256'] = sha(helper)
        result['shared_build'] = str(shared)

        old_receipt_path = REF / 'charging-oem-audit-20261023/gauge-current-samurai-candidate/build-result.json'
        old = json.loads(old_receipt_path.read_bytes())
        assert old['passed'] and sha(Path(old['object_private'])) == old['object_sha256']
        assert old['object_sha256'] == '6809ee2b777e7c2d69bd38570a0ecab5ce72a7cb16f47bbaf8ee112de669e125'
        assert sha(SOURCE / 'drivers/power/supply/bq27xxx_battery.c') == old['source_sha256']
        assert old['source_sha256'] == '0aa3c533bab0ec9219364af5328d353334cbf5112f97c8529aa162f95fd88ffe'
        saved = BUILD / 'drivers/power/supply/.bq27xxx_battery.o.cmd'
        assert sha(saved) == '70f9570bf92af235b50c730f7afa1d9cc6f52eaefe2b2b2e099268210e675827'
        row = saved.read_text().splitlines()[0]
        assert row.startswith('savedcmd_drivers/power/supply/bq27xxx_battery.o := ')
        argv = shlex.split(row.split(' := ', 1)[1])
        assert argv[0] == 'aarch64-linux-gnu-gcc' and '-DKBUILD_EXTRA_WARN1' in argv
        assert argv[-1] == str(SOURCE / 'drivers/power/supply/bq27xxx_battery.c')
        assert argv.count('-o') == 1
        dep = '-Wp,-MMD,drivers/power/supply/.bq27xxx_battery.o.d'
        assert argv.count(dep) == 1

        paths = [Path(p) for p in old['shared_inputs_before']]
        paths += [BUILD / n for n in ['.config', 'include/generated/autoconf.h',
                  'include/generated/utsrelease.h', 'drivers/power/supply/.bq27xxx_battery.o.cmd',
                  'drivers/power/supply/bq27xxx_battery.o']]
        paths += [SOURCE / 'drivers/power/supply/bq27xxx_battery.c']
        paths += [shared / n for n in ['include/generated/autoconf.h', 'include/generated/utsrelease.h']]
        before = {str(p): sha(p) for p in paths}
        assert all(before[p] == h for p, h in old['shared_inputs_before'].items())
        assert before[str(BUILD / '.config')] == old['private_config_sha256']
        argv[-1] = str(HERE / 'bq27xxx_battery.c')
        argv[argv.index('-o') + 1] = str(OUT / 'bq27xxx_battery.o')
        argv[argv.index(dep)] = '-Wp,-MMD,' + str(OUT / 'bq27xxx_battery.d')
        argv.insert(1, '-Werror')
        result.update(command=argv, cwd=str(BUILD), before=before,
                      saved_command_sha256=sha(saved), original_object_receipt_sha256=sha(old_receipt_path),
                      test_receipt_sha256=sha(HERE / 'test-result.json'), candidate_files=expected,
                      build_script_sha256=sha(Path(__file__)))
        started = time.monotonic()
        proc = subprocess.Popen(argv, cwd=BUILD, env={**os.environ, 'TMPDIR': str(OUT / 'tmp')},
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        result.update(compiler_invoked=True, compiler_pid=proc.pid)
        stdout, stderr = proc.communicate()
        (OUT / 'stdout').write_bytes(stdout)
        (OUT / 'stderr').write_bytes(stderr)
        after = {str(p): sha(p) for p in paths}
        result.update(returncode=proc.returncode, terminal=True, seconds=time.monotonic() - started,
                      stdout_sha256=sha(OUT / 'stdout'), stderr_sha256=sha(OUT / 'stderr'),
                      diagnostic_bytes=len(stderr), after=after, tracked_inputs_unchanged=before == after,
                      object_sha256=sha(OUT / 'bq27xxx_battery.o') if (OUT / 'bq27xxx_battery.o').exists() else None)
        result['passed'] = proc.returncode == 0 and not stderr and before == after
    except Exception as error:
        result['error'] = type(error).__name__ + ': ' + str(error)
    (OUT / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    (HERE / 'object-build-result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps({key: result.get(key) for key in ['passed', 'compiler_invoked', 'terminal',
                     'returncode', 'object_sha256', 'diagnostic_bytes', 'tracked_inputs_unchanged', 'error']}))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    run()
