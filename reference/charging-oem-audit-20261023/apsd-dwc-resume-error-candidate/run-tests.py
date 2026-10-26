"""Execute only the changed resume-common path and preserved old counterexample."""
from pathlib import Path
import hashlib
import json
import subprocess
import tempfile
import prepare

ROOT=Path(__file__).resolve().parent
def main():
    prepare.main()
    flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter',
           '-fsanitize=address,undefined','-fno-omit-frame-pointer']
    with tempfile.TemporaryDirectory(prefix='dwc-resume-error-') as temp:
        binary=Path(temp)/'test'
        subprocess.run(['cc',*flags,str(ROOT/'test-resume.c'),'-o',str(binary)],check=True)
        r=subprocess.run([str(binary)],capture_output=True,text=True)
        assert r.returncode==0 and not r.stderr,(r.stdout,r.stderr)
    cases=[x[4:] for x in r.stdout.splitlines() if x.startswith('ok: ')]
    assert len(cases)==8
    report={'passed':True,'original_false_success_reproduced':True,'cases':cases,
        'actual_function':'dwc3_resume_common','flags':flags,
        'files_sha256':{n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in
         ['core.c','resume-error.patch','original-resume.inc','candidate-resume.inc','test-resume.c']},
        'r2_suites_rerun':False,'phone_accessed':False,'sdk_invoked':False,
        'real_pm_or_usb_recovery_accepted':False}
    (ROOT/'test-result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
