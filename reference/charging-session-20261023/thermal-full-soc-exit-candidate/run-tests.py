"""Host C fixtures only. Never use the kernel build tree, SDK or a device."""
from pathlib import Path
import argparse, hashlib, json, os, re, subprocess, sys, time
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
R8 = HERE.parent / 'r8-source-integration/kernel-sources/drivers/power/supply'
ORACLE = HERE.parent / 'thermal-bands-candidate'
REAT = HERE.parent / 'charger-reattach-observation-candidate'
PRIVATE = Path('/mnt/e/edk2-samurai-out/charging-session-20261023')
sha = lambda raw: hashlib.sha256(raw).hexdigest()


def execute(argv, out, label):
    with (out/(label+'.stdout-private.inc')).open('xb') as stdout, (out/(label+'.stderr-private.inc')).open('xb') as stderr:
        child = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        rc = child.wait(); stdout.flush(); stderr.flush()
        os.fsync(stdout.fileno()); os.fsync(stderr.fileno())
    return dict(pid=child.pid, argv=argv, terminal=True, returncode=rc,
                stdout_sha256=sha((out/(label+'.stdout-private.inc')).read_bytes()),
                stderr_sha256=sha((out/(label+'.stderr-private.inc')).read_bytes()))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--attempt',default='01');args=parser.parse_args()
    if not re.fullmatch('[0-9]{2}',args.attempt) or sys.flags.optimize: raise ValueError('explicit host fixture attempt/nonoptimized Python')
    source=(HERE/'samurai-mp2650.c').read_text(); bodies=[]; actual={}
    for name in ('sm_gauge_sample','sm_step_locked'):
        match=re.search(r'^static int '+name+r'\([^;{]*\)\s*\{',source,re.M)
        if not match: raise ValueError('actual function not found: '+name)
        end=source.index('\n}',match.end())+2;body=source[match.start():end]
        bodies.append(body);actual[name]={'sha256_lf':sha(body.encode()),'first_line':source[:match.start()].count('\n')+1}
    (HERE/'actual-functions.inc').write_bytes(('\n\n'.join(bodies)+'\n').encode())
    input_paths=[HERE/n for n in ('samurai-mp2650.c','mp2650-core.h','oem-full-cycle.h','actual-functions.inc','test-exit.c','run-tests.py')]
    input_paths += [R8/n for n in ('oem-profile.h','thermal-bands.h','charge-cycle.h','gauge-protocol.h')]
    input_paths += [REAT/'reattach-observation.h', ORACLE/'oracle-fixture.h', ORACLE/'oracle-functions.inc',
                    ORACLE/'oracle-limit-fields.inc',ORACLE/'oracle-limits.inc',ORACLE/'oracle-result.json']
    inputs={str(p):sha(p.read_bytes()) for p in input_paths}
    out=PRIVATE/('thermal-full-soc-exit-tests-private-'+args.attempt);out.mkdir(mode=0o700,parents=True,exist_ok=False)
    command=['gcc','-std=c11','-g','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-fno-omit-frame-pointer',
             '-I'+str(HERE),'-I'+str(R8),'-I'+str(REAT),'-I'+str(ORACLE),str(HERE/'test-exit.c'),'-o',str(out/'test-exit')]
    result={'passed':False,'device_accessed':False,'SDK_accessed':False,'kernel_built':False,'old_suites_rerun':False,
            'private_output':str(out),'inputs':inputs,'actual_functions':actual}
    result['compile']=execute(command,out,'compile')
    if result['compile']['returncode']==0:
        result['run']=execute([str(out/'test-exit')],out,'run')
        if result['run']['returncode']==0:
            result['summary']=json.loads((out/'run.stdout-private.inc').read_bytes());result['passed']=result['summary']['passed'] is True
    result['inputs_unchanged']=all(sha(Path(p).read_bytes())==digest for p,digest in inputs.items())
    result['passed']=result['passed'] and result['inputs_unchanged']
    raw=(json.dumps(result,indent=2)+'\n').encode()
    (out/'result-private.json').write_bytes(raw)
    target=HERE/('test-result.json' if result['passed'] else 'test-failure-'+args.attempt+'.json')
    with target.open('xb') as stream:stream.write(raw)
    print(json.dumps({'passed':result['passed'],'compile':result['compile']['returncode'],
                      'run':result.get('run',{}).get('returncode'),'summary':result.get('summary')}))
    if not result['passed']:raise SystemExit(1)


if __name__=='__main__':main()
