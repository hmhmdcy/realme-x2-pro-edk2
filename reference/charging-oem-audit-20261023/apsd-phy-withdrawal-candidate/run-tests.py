from pathlib import Path
import difflib,hashlib,importlib.util,json,re,subprocess,tempfile
HERE=Path(__file__).resolve().parent;OLD=HERE.parent/'apsd-phy-window-candidate'
sha=lambda raw:hashlib.sha256(raw).hexdigest()
source=(HERE/'phy-qcom-snps-femto-v2.c').read_text();header=(HERE/'phy-qcom-snps-femto-v2-window.h').read_text()
def function(name):
    m=re.search(r'^(?:static\s+)?(?:inline\s+)?(?:int|bool|void)\s+(?:__maybe_unused\s+)?'+name+r'\([^;]*?\)\s*\{',source,re.M);assert m,name
    start=m.start();i=source.index('{',start)+1;depth=1
    while depth:depth+=(source[i]=='{')-(source[i]=='}');i+=1
    return source[start:i]
names=['qcom_snps_hsphy_window_busy','qcom_snps_hsphy_window_write','qcom_snps_hsphy_window_bound_begin','qcom_snps_hsphy_window_bound_end',
       'qcom_snps_hsphy_write_mask','qcom_snps_hsphy_suspend','qcom_snps_hsphy_resume','qcom_snps_hsphy_runtime_suspend','qcom_snps_hsphy_runtime_resume',
       'qcom_snps_hsphy_set_mode','qcom_snps_hsphy_init','qcom_snps_hsphy_exit']
functions=[function(n) for n in names]
arrays='\n'.join(re.search(r'static const u32 '+n+r'\[\] = \{.*?\};',source,re.S).group() for n in
    ['qcom_snps_hsphy_window_offsets','qcom_snps_hsphy_window_masks','qcom_snps_hsphy_window_values'])
types=header[header.index('enum qcom_snps_hsphy_window_state'):header.rindex('#endif')]
macros='\n'.join(l for l in source.splitlines() if l.startswith('#define ') and not l.startswith('#define SNPS_HS_NUM_VREGS'))
structure=re.search(r'^struct qcom_snps_hsphy \{.*?^\};',source,re.M|re.S).group()
assert source.count((HERE/'provider-lifetime.inc').read_text())==1
inc='struct qcom_hsphy_window_provider;\n'+macros+'\n#define SNPS_HS_NUM_VREGS 3\n'+types+'\n'+structure
body='static const struct phy_ops qcom_snps_hsphy_gen_ops;\n'+arrays+'\n'+'\n\n'.join(functions[:4])+'\n'+(HERE/'provider-lifetime.inc').read_text()+'\n'+'\n\n'.join(functions[4:])
flags=['-std=gnu11','-Wall','-Wextra','-Werror','-Wno-unused-parameter','-Wno-sign-compare','-fsanitize=address,undefined','-fno-omit-frame-pointer','-pthread','-no-pie']
with tempfile.TemporaryDirectory(prefix='samurai-phy-withdrawal-') as name:
    root=Path(name);(root/'actual-types.inc').write_text(inc);(root/'actual-functions.inc').write_text(body)
    binary=root/'test';build=subprocess.run(['gcc',*flags,'-I'+str(root),str(HERE/'test-withdrawal.c'),'-o',str(binary)],capture_output=True,text=True)
    assert build.returncode==0,build.stderr
    run=subprocess.run([str(binary)],capture_output=True,text=True,timeout=30)
    assert run.returncode==0,(run.returncode,run.stdout,run.stderr)
    groups=[line[4:] for line in run.stdout.splitlines() if line.startswith('ok: ')];assert len(groups)==10 and not run.stderr
    (root/'drivers/phy/qualcomm').mkdir(parents=True)
    for n in ['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h']:(root/'drivers/phy/qualcomm'/n).write_bytes((OLD/n).read_bytes())
    check=subprocess.run(['patch','--fuzz=0','-p1','-i',str(HERE/'withdrawal.patch')],cwd=root,capture_output=True,text=True);assert check.returncode==0,check.stderr
    assert all((root/'drivers/phy/qualcomm'/n).read_bytes()==(HERE/n).read_bytes() for n in ['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h'])
result=dict(passed=True,groups=groups,group_count=len(groups),flags=flags,runtime_stdout=run.stdout,runtime_stderr=run.stderr,
    complete_provider_lifetime_bodies=True,actual_extracted_window_and_lifecycle_functions=names,
    body_sha256=sha(body.encode()),types_sha256=sha(inc.encode()),patch_applied_fuzz0_exact_bytes=True,
    files={n:sha((HERE/n).read_bytes()) for n in ['phy-qcom-snps-femto-v2.c','phy-qcom-snps-femto-v2-window.h','provider-lifetime.inc','prepare.py','run-tests.py','test-withdrawal.c','withdrawal.patch']},
    real_pthread_mutex_join_and_completion=True,PM_MMIO_and_driver_core_edges_modeled=True,phone_accessed=False,consumer_connected=False)
with (HERE/'test-result.json').open('x') as f:json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(dict(passed=True,groups=len(groups),phone_accessed=False)))
