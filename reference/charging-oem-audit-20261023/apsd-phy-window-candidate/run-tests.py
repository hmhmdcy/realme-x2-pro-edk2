from pathlib import Path
import hashlib,json,subprocess,tempfile
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(HERE/'prepare-tests.py')],check=True,capture_output=True)
flags=['-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer']
build=subprocess.run(['gcc',*flags,str(HERE/'test-window.c'),'-o',str(HERE/'test-window')],capture_output=True,text=True)
assert build.returncode==0,build.stderr
run=subprocess.run([str(HERE/'test-window')],capture_output=True,text=True)
assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
cases=[l[4:] for l in run.stdout.splitlines() if l.startswith('ok: ')]
assert len(cases)==8 and not run.stderr
with tempfile.TemporaryDirectory() as t:
 p=Path(t);(p/'drivers/phy/qualcomm').mkdir(parents=True)
 (p/'drivers/phy/qualcomm/phy-qcom-snps-femto-v2.c').write_bytes((HERE.parent/'apsd-integration/current-r7/snapshots/drivers--phy--qualcomm--phy-qcom-snps-femto-v2.c').read_bytes())
 q=subprocess.run(['patch','--dry-run','-p1','-i',str(HERE/'phy-window.patch')],cwd=p,capture_output=True,text=True)
 assert q.returncode==0,q.stderr
r=dict(passed=True,groups=cases,group_count=8,actual_functions=15,flags=flags,
 runtime_stdout=run.stdout,runtime_stderr=run.stderr,patch_dry_run=True,
 files={n:sha(HERE/n) for n in ['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h','phy-window.patch','test-window.c','tested-functions.inc','tested-types.inc','function-manifest.json','prepare-tests.py','run-tests.py']},
 no_new_consumer=True,phone_accessed=False,ssh_executed=False,sdk_invoked=False,
 scope='actual candidate+generic PHY functions; fake PM/MMIO/OS edges; not lockdep or physical validation')
(HERE/'test-result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({'passed':True,'groups':8,'functions':15}))
