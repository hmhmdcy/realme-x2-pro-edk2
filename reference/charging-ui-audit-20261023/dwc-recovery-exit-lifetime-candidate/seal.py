"""Bind frozen source review and the already-terminal single-object receipt."""
from pathlib import Path
import ast
import hashlib
import json
import sys
sys.dont_write_bytecode=True
HERE=Path(__file__).resolve().parent
REF=HERE.parents[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    if sys.flags.optimize:raise RuntimeError('Nonoptimized interpreter required')
    sd=HERE/'source-delivery.json'
    if sha(sd)!='4a645839ece5fd0273b3ff93beda9616593e94dc69215e9822295c76b6f26f07':
        raise ValueError('Source delivery')
    source=json.loads(sd.read_bytes())
    for n,item in source['files'].items():
        if sha(HERE/n)!=item['sha256']:raise ValueError(n)
    review=REF/'charging-session-20261023/dwc-recovery-exit-lifetime-independent-review/review-result.json'
    if sha(review)!='1e671908ce129a7928950976abdd48edfe577a748955b5acf48a80cc04d1a147':
        raise ValueError('Review')
    r=json.loads(review.read_bytes())
    if not r['passed'] or r['author_source_delivery_sha256']!=sha(sd):raise ValueError('Reviewed source')
    build=HERE/'object-build/build-result.json';b=json.loads(build.read_bytes())
    if not b['passed'] or not b['phase']['terminal'] or b['phase']['returncode']!=0:
        raise ValueError('Terminal object compile')
    if b['source_delivery_sha256']!=sha(sd) or not b['tracked_inputs_unchanged']:
        raise ValueError('Build source')
    if b['inputs_before']!=b['inputs_after'] or not b['parent_mounts_unchanged_after_helper']:
        raise ValueError('Unchanged inputs')
    if b['diagnostic_lines'] or b['object_sha256']!='e6af6ad4dfee3e053b1e3dd4dad28325dd22d74d1d5f8683d3bbf576abdbbed2':
        raise ValueError('Object')
    names=list(source['files'])+['source-delivery.json','object-build/build-object.py',
                                'object-build/build-result.json','object-build/README.md','seal.py']
    for n in names:
        if n.endswith('.py'):ast.parse((HERE/n).read_bytes(),filename=n)
    if sha(HERE/'object-build/build-object.py')!=b['files']['build-object.py']:
        raise ValueError('Executed builder')
    result=dict(schema=1,passed=True,frozen=True,
        scope='exit-only recovery enqueue/work/mutex lifetime; no PM consumer',
        files={n:dict(sha256=sha(HERE/n),bytes=(HERE/n).stat().st_size) for n in names},
        source_delivery_sha256=sha(sd),independent_review=dict(path=review.relative_to(REF).as_posix(),sha256=sha(review)),
        build_result_sha256=sha(build),new_actual_cases=8,old_suites_rerun=False,
        original_exec_session=86801,original_exec_terminal_exit_code=0,
        sole_compiler_pid=b['phase']['pid'],single_target_W1_Werror_passed=True,
        private_object_sha256=b['object_sha256'],private_object_bytes=b['object_size'],
        source_and_shared_inputs_unchanged=True,volume_window_returned_after_terminal=True,
        all_new_header_consumers_rebuilt=False,full_suspend_ACTIVE_I_O_recovery_proved=False,
        full_resume_abort_proved=False,Image_module_or_firmware_generated=False,
        deployed=False,device_SSH_USB_SDK_Git_used=False)
    (HERE/'delivery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(passed=True,delivery_sha256=sha(HERE/'delivery.json'),
                         build_result_sha256=sha(build),files=len(names))))


if __name__=='__main__':main()
