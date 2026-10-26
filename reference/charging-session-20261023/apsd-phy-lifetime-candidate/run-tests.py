from pathlib import Path
import hashlib,json,os,subprocess
H=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
subprocess.run(['python3',str(H/'prepare-tests.py')],check=True)
O=H/'test-private';O.mkdir(exist_ok=True)
flags=['-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-unused-function','-Wno-sign-compare','-pthread','-fsanitize=address,undefined','-fno-omit-frame-pointer','-g']
c=subprocess.run(['gcc',*flags,str(H/'test-lifecycle.c'),'-o',str(O/'test-lifecycle')],capture_output=True,text=True)
(O/'compile.stdout').write_text(c.stdout);(O/'compile.stderr').write_text(c.stderr)
assert c.returncode==0,c.stderr
p=subprocess.run([str(O/'test-lifecycle')],capture_output=True,text=True,timeout=30,env={**os.environ,'ASAN_OPTIONS':'detect_leaks=1:abort_on_error=1'})
(O/'run.stdout').write_text(p.stdout);(O/'run.stderr').write_text(p.stderr)
assert p.returncode==0,(p.returncode,p.stdout,p.stderr)
groups=[l[4:] for l in p.stdout.splitlines() if l.startswith('ok: ')]
assert len(groups)==9 and not p.stderr
names=['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h','phy-lifetime.inc','samurai-apsd-owner.c','samurai-apsd-owner.h','prepare-tests.py','test-lifecycle.c','run-tests.py','tested-functions.inc','tested-types.inc','tested-owner.inc','function-manifest.json']
r=dict(passed=True,groups=groups,affected_groups=len(groups),flags=flags,tested_files={n:sha(H/n) for n in names},
 actual_extracted_functions=len(json.loads((H/'function-manifest.json').read_bytes())),
 lifecycle_include_actual=True,old_owner_join_is_fake_boundary=True,scope='new provider/DWC lifecycle and races; pthread/fake OS+PM+MMIO+devres, not kernel lockdep or hardware',
 old_phy_8_reused_not_rerun=True,old_pd_bridge_14_reused_not_rerun=True,device_accessed=False,SDK_invoked=False,
 stdout=p.stdout,stderr=p.stderr)
(H/'test-result.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps(dict(passed=True,groups=len(groups),test_result_sha256=sha(H/'test-result.json'))))
