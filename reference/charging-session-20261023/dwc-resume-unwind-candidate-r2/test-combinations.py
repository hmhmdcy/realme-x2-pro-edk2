"""Only seven current call-chain controls, native GCC in new private /home output."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time
HERE = Path(__file__).resolve().parent
OUT = Path('/home/cy122/charging-management-20261023/dwc-resume-unwind-r2-test-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if sys.flags.optimize or os.name == 'nt': raise RuntimeError('run only as the explicit nonoptimized native Linux fixture')
assert not OUT.exists(), 'unique private fixture output; inspect original handle, never replay'
source = json.loads((HERE / 'source-result.json').read_bytes())
REF = HERE.parents[1]
for name, digest in source['inputs'].items(): assert sha(REF / name) == digest
OUT.mkdir(parents=True)
flags = ['gcc', '-std=c11', '-Wall', '-Wextra', '-Werror', '-Wno-unused-function', '-Wno-unused-parameter',
    '-g', '-O1', '-fsanitize=address,undefined', '-fno-omit-frame-pointer', '-fno-pie', '-no-pie']
phases = []
for phase, argv in [('compile', flags + [str(HERE / 'test-combinations.c'), '-o', str(OUT / 'test-combinations')]),
                    ('run', [str(OUT / 'test-combinations')])]:
    start = time.monotonic()
    with (OUT / (phase + '.stdout')).open('wb') as stdout, (OUT / (phase + '.stderr')).open('wb') as stderr:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
            env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1', UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
        print(json.dumps(dict(phase=phase, pid=child.pid)), flush=True)
        rc = child.wait()
    phases.append(dict(phase=phase, argv=argv, pid=child.pid, terminal=True, returncode=rc,
        seconds=time.monotonic() - start, stdout_sha256=sha(OUT / (phase + '.stdout')), stderr_sha256=sha(OUT / (phase + '.stderr'))))
    if rc:
        print((OUT / (phase + '.stderr')).read_text(), flush=True); break
summary = None
if len(phases) == 2 and phases[-1]['returncode'] == 0:
    summary = json.loads((OUT / 'run.stdout').read_text().splitlines()[-1])
passed = bool(summary and summary['passed'] is True and summary['cases'] == 7)
unchanged = all(sha(REF / name) == digest for name, digest in source['inputs'].items())
result = dict(passed=passed and unchanged, summary=summary, phases=phases, private_output=str(OUT),
    original_frozen_sources_unchanged=unchanged, actual_functions=17, new_combined_cases=7,
    safe_gadget_failure_unwind_proved=False, deployable_patch_generated=False,
    boundaries='fake MMIO/PHY/init/endpoint/IRQ/work/PM APIs; exact extracted gadget/core caller and control bodies',
    runtime_PM_status_failure_transition='explicit adapter from cached actual runtime.c, not whole runtime engine simulation',
    old_13_20_24_126_suites_rerun=False, storage_guard_object_Image_SDK_device_Git_used=False,
    files={name: sha(HERE / name) for name in ['extract.py', 'source-result.json', 'actual-functions.inc',
        'rejected-diagnostic-functions.inc', 'test-combinations.c', 'test-combinations.py']})
(HERE / 'test-result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(dict(passed=result['passed'], summary=summary, receipt_sha256=sha(HERE / 'test-result.json'))), flush=True)
raise SystemExit(0 if result['passed'] else 1)
