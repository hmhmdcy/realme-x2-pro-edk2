"""Only new stack-result branches and legacy differential controls. No old suite."""
from pathlib import Path
import hashlib, json, os, subprocess, sys, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REF = HERE.parents[1]
OUT = Path('/home/cy122/charging-management-20261023/dwc-device-resume-outcome-test-01')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
if sys.flags.optimize or os.name == 'nt':
    raise RuntimeError('explicit nonoptimized native Linux fixture required')
source = json.loads((HERE/'source-result.json').read_bytes())
for name, digest in source['source_inputs'].items():
    assert sha(REF/name) == digest, name
for name, digest in source['candidate_sha256'].items():
    assert sha(HERE/name) == digest, name
assert not OUT.exists(), 'unique private output; follow its original process, never replay'
OUT.mkdir(parents=True)
flags = ['gcc','-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-parameter',
         '-g','-O1','-fsanitize=address,undefined','-fno-omit-frame-pointer','-fno-pie','-no-pie']
phases = []
summaries = []
for name in ['test-outcome', 'test-host-stub']:
    for label, argv in [(name+'-compile', flags+[str(HERE/(name+'.c')), '-o', str(OUT/name)]),
                        (name+'-run', [str(OUT/name)])]:
        started = time.monotonic()
        with (OUT/(label+'.stdout')).open('wb') as stdout, (OUT/(label+'.stderr')).open('wb') as stderr:
            child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr,
                env=dict(os.environ, ASAN_OPTIONS='detect_leaks=1:abort_on_error=1',
                         UBSAN_OPTIONS='halt_on_error=1:print_stacktrace=1'))
            try:
                print(json.dumps(dict(phase=label, pid=child.pid)), flush=True)
            finally:
                rc = child.wait()
        phases.append(dict(phase=label, argv=argv, pid=child.pid, terminal=True, returncode=rc,
            seconds=time.monotonic()-started, stdout_sha256=sha(OUT/(label+'.stdout')),
            stderr_sha256=sha(OUT/(label+'.stderr'))))
        if rc:
            print((OUT/(label+'.stderr')).read_text(), flush=True)
            break
        if label.endswith('-run'):
            summaries.append(json.loads((OUT/(label+'.stdout')).read_text().splitlines()[-1]))
    if phases[-1]['returncode']:
        break
passed = len(summaries)==2 and summaries[0]['cases']==18 and summaries[1]['cases']==1
unchanged = all(sha(REF/name)==digest for name,digest in source['source_inputs'].items())
files = ['prepare.py','source-result.json','gadget.c','core.h','device-resume-outcome.patch',
         'actual-functions.inc','previous-resume.inc','host-stubs.inc',
         'test-outcome.c','test-host-stub.c','test-outcome.py']
result = dict(passed=passed and unchanged, summaries=summaries, phases=phases,
    files={n:sha(HERE/n) for n in files}, private_output=str(OUT),
    original_frozen_inputs_unchanged=unchanged,
    new_outcome_cases=18, HOST_stub_cases=1, legacy_differential_scenarios=16,
    old_7_15_13_24_20_126_suites_rerun=False,
    boundaries='MMIO/endpoint/IRQ scheduling/PM state fake; exact candidate gadget functions and actual header stub',
    core_consumer_added=False, PM_unwind_proved=False, object_or_Image_built=False,
    device_SSH_USB_storage_helper_SDK_Git_used=False)
(HERE/'test-result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(dict(passed=result['passed'], summaries=summaries,
                     test_result_sha256=sha(HERE/'test-result.json'))),flush=True)
raise SystemExit(0 if result['passed'] else 1)
